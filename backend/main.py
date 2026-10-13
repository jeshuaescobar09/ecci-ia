
import functools
import secrets
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from flask import Flask, abort, jsonify, request, send_from_directory
from pymongo.errors import DuplicateKeyError, PyMongoError
from werkzeug.middleware.proxy_fix import ProxyFix

import config
from db import get_db
from imagenes import ErrorImagen, borrar_imagen, guardar_imagen
from limitador import Limitador
from validaciones import (
    ErrorValidacion,
    limpiar,
    validar_comentario,
    validar_noticia,
    validar_opinion,
    validar_video,
    validar_visitante,
)

app = Flask(__name__, static_folder=None)

# En Render (u otro hosting) las visitas pasan por un proxy: así vemos la IP real de cada persona
if config.DETRAS_DE_PROXY:
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

app.config["MAX_CONTENT_LENGTH"] = (config.MAX_IMAGEN_MB + 1) * 1024 * 1024
app.json.ensure_ascii = False
config.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

limite_envios = Limitador(config.LIMITE_ENVIOS, config.VENTANA_ENVIOS)
limite_admin = Limitador(10, 600)
limite_likes = Limitador(60, 600)  # dar y quitar «me gusta» es más frecuente que enviar textos

MENSAJE_NOTICIA = "Recibimos tu noticia. Quedó pendiente de aprobación; la revisaremos antes de publicarla."
MENSAJE_OPINION = "Gracias por opinar. Tu opinión se publicará cuando un moderador la apruebe."
MENSAJE_VIDEO = "Recibimos tu video. Quedó pendiente de aprobación; lo revisaremos antes de publicarlo."
MENSAJE_COMENTARIO = "Gracias por comentar. Tu comentario se publicará cuando un moderador lo apruebe."
ESTADOS = ("pendiente", "aprobada", "rechazada")
TIPOS = ("noticias", "opiniones", "videos", "comentarios")
RECIENTES = [("fecha_publicacion", -1), ("_id", -1)]
RECIBIDAS = [("fecha_creacion", -1), ("_id", -1)]



class ErrorApi(Exception):
    def __init__(self, estado, mensaje):
        super().__init__(mensaje)
        self.estado = estado
        self.mensaje = mensaje


@app.errorhandler(ErrorApi)
def _error_api(e):
    return jsonify(detail=e.mensaje), e.estado


@app.errorhandler(ErrorValidacion)
def _error_validacion(e):
    return jsonify(detail=e.mensaje), 422


@app.errorhandler(ErrorImagen)
def _error_imagen(e):
    return jsonify(detail=e.mensaje), e.estado


@app.errorhandler(PyMongoError)
def _error_bd(e):
    return jsonify(detail="No hay conexión con la base de datos. Intenta de nuevo en un momento."), 503


@app.errorhandler(413)
def _demasiado_grande(e):
    return jsonify(detail="El envío es demasiado grande (la imagen puede pesar hasta %d MB)." % config.MAX_IMAGEN_MB), 413


@app.errorhandler(404)
def _no_encontrado(e):
    if request.path.startswith("/api/"):
        return jsonify(detail="No encontrado."), 404
    return "No encontrado", 404


@app.errorhandler(405)
def _metodo(e):
    return jsonify(detail="Método no permitido."), 405


@app.errorhandler(500)
def _error_interno(e):
    return jsonify(detail="Error interno del servidor."), 500



@app.after_request
def _cabeceras(respuesta):
    respuesta.headers.setdefault("X-Content-Type-Options", "nosniff")
    respuesta.headers.setdefault("X-Frame-Options", "DENY")
    respuesta.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")

    if request.path.startswith("/api/admin"):
        respuesta.headers["Cache-Control"] = "no-store"

    origen = request.headers.get("Origin")
    if origen and request.path.startswith("/api/"):
        if origen in config.CORS_ORIGINS or "*" in config.CORS_ORIGINS:
            respuesta.headers["Access-Control-Allow-Origin"] = origen
            respuesta.headers["Vary"] = "Origin"
            respuesta.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Admin-Key"
            respuesta.headers["Access-Control-Allow-Methods"] = "GET, POST, DELETE, OPTIONS"
    return respuesta



def bd():
    try:
        return get_db()
    except RuntimeError as e:
        raise ErrorApi(503, str(e))


def _ip():
    return request.remote_addr or "desconocida"


def _ahora():
    return datetime.now(timezone.utc)


def _iso(valor):
    if not isinstance(valor, datetime):
        return None
    if valor.tzinfo is None:
        valor = valor.replace(tzinfo=timezone.utc)
    return valor.astimezone(timezone.utc).isoformat()


def _oid(valor):
    try:
        return ObjectId(valor)
    except (InvalidId, TypeError):
        raise ErrorApi(404, "No encontrado.")


def _entero(valor, defecto, minimo, maximo):
    try:
        n = int(valor)
    except (TypeError, ValueError):
        return defecto
    return max(minimo, min(maximo, n))


def _noticia_publica(doc, completa=False):
    
    salida = {
        "id": str(doc["_id"]),
        "titulo": doc.get("titulo", ""),
        "resumen": doc.get("resumen", ""),
        "categoria": doc.get("categoria", ""),
        "autor": doc.get("autor", ""),
        "imagen_url": doc.get("imagen_url"),
        "fecha": _iso(doc.get("fecha_publicacion")),
    }
    if completa:
        salida["contenido"] = doc.get("contenido", "")
    return salida


def _opinion_publica(doc, comentarios=(), me_gusta=False):
    return {
        "id": str(doc["_id"]),
        "nombre": doc.get("nombre", ""),
        "tema": doc.get("tema", ""),
        "texto": doc.get("texto", ""),
        "fecha": _iso(doc.get("fecha_publicacion")),
        "likes": max(0, doc.get("likes", 0)),
        "me_gusta": me_gusta,
        "comentarios": [_comentario_publico(c) for c in comentarios],
    }


def _comentario_publico(doc):
    return {
        "id": str(doc["_id"]),
        "nombre": doc.get("nombre", ""),
        "texto": doc.get("texto", ""),
        "fecha": _iso(doc.get("fecha_publicacion")),
    }


def _video_publico(doc):
    return {
        "id": str(doc["_id"]),
        "titulo": doc.get("titulo", ""),
        "categoria": doc.get("categoria", ""),
        "descripcion": doc.get("descripcion", ""),
        "autor": doc.get("autor", ""),
        "youtube_id": doc.get("youtube_id", ""),
        "fecha": _iso(doc.get("fecha_publicacion")),
    }


def _doc_admin(doc):
    salida = {k: v for k, v in doc.items() if k != "_id"}
    salida["id"] = str(doc["_id"])
    for clave, valor in list(salida.items()):
        if isinstance(valor, datetime):
            salida[clave] = _iso(valor)
        elif isinstance(valor, ObjectId):
            salida[clave] = str(valor)
    return salida


def _limitar_envios(tipo):
    if limite_envios.excedido("%s:%s" % (tipo, _ip())):
        raise ErrorApi(429, "Has enviado varias veces seguidas. Espera unos minutos e inténtalo de nuevo.")



@app.get("/api/salud")
def salud():
    estado = {"ok": True, "base_de_datos": False}
    try:
        get_db().command("ping")
        estado["base_de_datos"] = True
    except Exception:
        pass
    return jsonify(estado)


@app.get("/api/noticias")
def listar_noticias():
    limite = _entero(request.args.get("limite"), 12, 1, 50)
    pagina = _entero(request.args.get("pagina"), 1, 1, 100000)
    col = bd().noticias
    filtro = {"estado": "aprobada"}
    cursor = col.find(filtro).sort(RECIENTES).skip((pagina - 1) * limite).limit(limite)
    return jsonify(total=col.count_documents(filtro), items=[_noticia_publica(d) for d in cursor])


@app.get("/api/noticias/aleatorias")
def noticias_aleatorias():
    n = _entero(request.args.get("n"), 3, 1, 12)
    docs = bd().noticias.aggregate([{"$match": {"estado": "aprobada"}}, {"$sample": {"size": n}}])
    return jsonify([_noticia_publica(d) for d in docs])


@app.get("/api/noticias/ultima")
def ultima_noticia():
    doc = bd().noticias.find_one({"estado": "aprobada"}, sort=RECIENTES)
    if not doc:
        raise ErrorApi(404, "Todavía no hay noticias publicadas.")
    return jsonify(_noticia_publica(doc, completa=True))


@app.get("/api/noticias/<noticia_id>")
def ver_noticia(noticia_id):
    doc = bd().noticias.find_one({"_id": _oid(noticia_id), "estado": "aprobada"})
    if not doc:
        raise ErrorApi(404, "No encontrado.")
    return jsonify(_noticia_publica(doc, completa=True))


@app.post("/api/noticias")
def crear_noticia():
    campos = request.form
    if limpiar(campos.get("sitio_web")):
        return jsonify(mensaje=MENSAJE_NOTICIA), 201

    _limitar_envios("noticia")
    datos = validar_noticia(campos)
    col = bd().noticias

    imagen_url = None
    archivo = request.files.get("imagen")
    if archivo and archivo.filename:
        imagen_url = guardar_imagen(archivo)

    ahora = _ahora()
    doc = dict(
        datos,
        imagen_url=imagen_url,
        estado="pendiente",
        motivo_rechazo=None,
        fecha_creacion=ahora,
        fecha_publicacion=None,
    )
    try:
        resultado = col.insert_one(doc)
    except Exception:
        borrar_imagen(imagen_url)
        raise

    limite_envios.registrar("noticia:" + _ip())
    return jsonify(mensaje=MENSAJE_NOTICIA, id=str(resultado.inserted_id)), 201


@app.get("/api/opiniones")
def listar_opiniones():
    limite = _entero(request.args.get("limite"), 20, 1, 50)
    base = bd()
    opiniones = list(base.opiniones.find({"estado": "aprobada"}).sort(RECIENTES).limit(limite))
    ids = [o["_id"] for o in opiniones]

    # Los comentarios aprobados de todas las opiniones, en una sola consulta (los más viejos primero)
    por_opinion = {}
    filtro = {"opinion_id": {"$in": ids}, "estado": "aprobada"}
    for c in base.comentarios.find(filtro).sort([("fecha_publicacion", 1), ("_id", 1)]):
        por_opinion.setdefault(c["opinion_id"], []).append(c)

    # Si el navegador manda su identificador, marcamos las opiniones a las que ya les dio «me gusta»
    mios = set()
    visitante = limpiar(request.args.get("visitante")).lower()
    if visitante:
        claves = ["%s:%s" % (i, visitante) for i in ids]
        mios = {m["opinion_id"] for m in base.me_gusta.find({"_id": {"$in": claves}})}

    return jsonify(items=[_opinion_publica(o, por_opinion.get(o["_id"], []), o["_id"] in mios) for o in opiniones])


@app.post("/api/opiniones")
def crear_opinion():
    campos = request.get_json(silent=True)
    if not isinstance(campos, dict):
        raise ErrorApi(400, "Datos no válidos.")
    if limpiar(campos.get("sitio_web")):
        return jsonify(mensaje=MENSAJE_OPINION), 201

    _limitar_envios("opinion")
    datos = validar_opinion(campos)
    col = bd().opiniones
    doc = dict(
        datos,
        estado="pendiente",
        motivo_rechazo=None,
        fecha_creacion=_ahora(),
        fecha_publicacion=None,
    )
    resultado = col.insert_one(doc)
    limite_envios.registrar("opinion:" + _ip())
    return jsonify(mensaje=MENSAJE_OPINION, id=str(resultado.inserted_id)), 201


def _opinion_aprobada(opinion_id):
    oid = _oid(opinion_id)
    if not bd().opiniones.find_one({"_id": oid, "estado": "aprobada"}):
        raise ErrorApi(404, "Esa opinión no existe o ya no está publicada.")
    return oid


@app.post("/api/opiniones/<opinion_id>/comentarios")
def crear_comentario(opinion_id):
    campos = request.get_json(silent=True)
    if not isinstance(campos, dict):
        raise ErrorApi(400, "Datos no válidos.")
    if limpiar(campos.get("sitio_web")):
        return jsonify(mensaje=MENSAJE_COMENTARIO), 201

    _limitar_envios("comentario")
    datos = validar_comentario(campos)
    oid = _opinion_aprobada(opinion_id)
    doc = dict(
        datos,
        opinion_id=oid,
        estado="pendiente",
        motivo_rechazo=None,
        fecha_creacion=_ahora(),
        fecha_publicacion=None,
    )
    resultado = bd().comentarios.insert_one(doc)
    limite_envios.registrar("comentario:" + _ip())
    return jsonify(mensaje=MENSAJE_COMENTARIO, id=str(resultado.inserted_id)), 201


def _cambiar_me_gusta(opinion_id, dar):
    campos = request.get_json(silent=True)
    if not isinstance(campos, dict):
        raise ErrorApi(400, "Datos no válidos.")
    if limite_likes.excedido(_ip()):
        raise ErrorApi(429, "Vas muy rápido. Espera unos minutos e inténtalo de nuevo.")
    visitante = validar_visitante(campos.get("visitante"))
    oid = _opinion_aprobada(opinion_id)
    limite_likes.registrar(_ip())

    base = bd()
    clave = "%s:%s" % (oid, visitante)
    if dar:
        try:
            base.me_gusta.insert_one({"_id": clave, "opinion_id": oid, "visitante": visitante, "fecha": _ahora()})
            base.opiniones.update_one({"_id": oid}, {"$inc": {"likes": 1}})
        except DuplicateKeyError:
            pass  # ya le había dado «me gusta»: no se cuenta dos veces
    elif base.me_gusta.delete_one({"_id": clave}).deleted_count:
        base.opiniones.update_one({"_id": oid}, {"$inc": {"likes": -1}})

    likes = base.opiniones.find_one({"_id": oid}).get("likes", 0)
    return jsonify(likes=max(0, likes), me_gusta=dar)


@app.post("/api/opiniones/<opinion_id>/me-gusta")
def dar_me_gusta(opinion_id):
    return _cambiar_me_gusta(opinion_id, True)


@app.delete("/api/opiniones/<opinion_id>/me-gusta")
def quitar_me_gusta(opinion_id):
    return _cambiar_me_gusta(opinion_id, False)


@app.get("/api/videos")
def listar_videos():
    limite = _entero(request.args.get("limite"), 6, 1, 30)
    cursor = bd().videos.find({"estado": "aprobada"}).sort(RECIENTES).limit(limite)
    return jsonify(items=[_video_publico(d) for d in cursor])


@app.post("/api/videos")
def crear_video():
    # El video vive en YouTube: aquí solo se guarda su identificador, nunca el archivo
    campos = request.get_json(silent=True)
    if not isinstance(campos, dict):
        raise ErrorApi(400, "Datos no válidos.")
    if limpiar(campos.get("sitio_web")):
        return jsonify(mensaje=MENSAJE_VIDEO), 201

    _limitar_envios("video")
    datos = validar_video(campos)
    doc = dict(
        datos,
        estado="pendiente",
        motivo_rechazo=None,
        fecha_creacion=_ahora(),
        fecha_publicacion=None,
    )
    resultado = bd().videos.insert_one(doc)
    limite_envios.registrar("video:" + _ip())
    return jsonify(mensaje=MENSAJE_VIDEO, id=str(resultado.inserted_id)), 201



def requiere_admin(funcion):
    @functools.wraps(funcion)
    def envoltura(*args, **kwargs):
        if not config.clave_admin_valida():
            raise ErrorApi(
                503,
                "El panel de moderación está desactivado: define ADMIN_KEY en backend/.env "
                "(mínimo 12 caracteres, distinta a la de ejemplo).",
            )
        ip = _ip()
        if limite_admin.excedido(ip):
            raise ErrorApi(429, "Demasiados intentos fallidos. Espera unos minutos.")
        enviada = request.headers.get("X-Admin-Key", "")
        if not secrets.compare_digest(enviada.encode("utf-8"), config.ADMIN_KEY.encode("utf-8")):
            limite_admin.registrar(ip)
            raise ErrorApi(401, "Clave incorrecta.")
        return funcion(*args, **kwargs)

    return envoltura


def _coleccion(tipo):
    if tipo not in TIPOS:
        raise ErrorApi(404, "No encontrado.")
    return bd()[tipo]


def _contar_por_estado(col):
    # Una sola consulta por colección (antes eran tres: una por estado)
    conteo = dict.fromkeys(ESTADOS, 0)
    for fila in col.aggregate([{"$group": {"_id": "$estado", "n": {"$sum": 1}}}]):
        if fila["_id"] in conteo:
            conteo[fila["_id"]] = fila["n"]
    return conteo


@app.get("/api/admin/resumen")
@requiere_admin
def admin_resumen():
    base = bd()
    return jsonify({t: _contar_por_estado(base[t]) for t in TIPOS})


@app.get("/api/admin/<tipo>")
@requiere_admin
def admin_listar(tipo):
    col = _coleccion(tipo)
    estado = request.args.get("estado", "pendiente")
    if estado not in ESTADOS + ("todas",):
        raise ErrorApi(422, "Estado no válido.")
    limite = _entero(request.args.get("limite"), 100, 1, 200)
    filtro = {} if estado == "todas" else {"estado": estado}
    items = [_doc_admin(d) for d in col.find(filtro).sort(RECIBIDAS).limit(limite)]
    if tipo == "comentarios":
        # El moderador necesita ver a qué opinión responde cada comentario
        ids = list({_oid(c["opinion_id"]) for c in items if c.get("opinion_id")})
        opiniones = {str(o["_id"]): o for o in bd().opiniones.find({"_id": {"$in": ids}})}
        for c in items:
            o = opiniones.get(c.get("opinion_id"))
            c["opinion"] = {"nombre": o.get("nombre", ""), "texto": o.get("texto", "")} if o else None
    return jsonify(items=items)


@app.post("/api/admin/<tipo>/<item_id>/aprobar")
@requiere_admin
def admin_aprobar(tipo, item_id):
    col = _coleccion(tipo)
    oid = _oid(item_id)
    doc = col.find_one({"_id": oid})
    if not doc:
        raise ErrorApi(404, "No encontrado.")
    if doc.get("estado") != "aprobada":
        col.update_one(
            {"_id": oid},
            {"$set": {"estado": "aprobada", "fecha_publicacion": _ahora(), "motivo_rechazo": None}},
        )
    return jsonify(ok=True, estado="aprobada")


@app.post("/api/admin/<tipo>/<item_id>/rechazar")
@requiere_admin
def admin_rechazar(tipo, item_id):
    col = _coleccion(tipo)
    oid = _oid(item_id)
    cuerpo = request.get_json(silent=True)
    motivo = limpiar(cuerpo.get("motivo")) if isinstance(cuerpo, dict) else ""
    if len(motivo) > 300:
        raise ErrorApi(422, "El motivo es muy largo (máximo 300 caracteres).")
    resultado = col.update_one(
        {"_id": oid},
        {"$set": {"estado": "rechazada", "fecha_publicacion": None, "motivo_rechazo": motivo or None}},
    )
    if not resultado.matched_count:
        raise ErrorApi(404, "No encontrado.")
    return jsonify(ok=True, estado="rechazada")


@app.delete("/api/admin/<tipo>/<item_id>")
@requiere_admin
def admin_eliminar(tipo, item_id):
    col = _coleccion(tipo)
    doc = col.find_one_and_delete({"_id": _oid(item_id)})
    if not doc:
        raise ErrorApi(404, "No encontrado.")
    if tipo == "noticias":
        borrar_imagen(doc.get("imagen_url"))
    if tipo == "opiniones":
        # Sin la opinión, sus comentarios y «me gusta» ya no tienen dónde mostrarse
        bd().comentarios.delete_many({"opinion_id": doc["_id"]})
        bd().me_gusta.delete_many({"opinion_id": doc["_id"]})
    return jsonify(ok=True)



ARCHIVOS_PUBLICOS = {
    "index.html", "admin.html", "styles.css", "extra.css", "app.js",
    "tema-diario.css", "animaciones.css", "animaciones.js",
}


@app.get("/")
def pagina_inicio():
    return send_from_directory(config.FRONTEND_DIR, "index.html")


@app.get("/admin")
def pagina_admin():
    return send_from_directory(config.FRONTEND_DIR, "admin.html")


@app.get("/<nombre>")
def archivo_publico(nombre):
    if nombre not in ARCHIVOS_PUBLICOS:
        abort(404)
    return send_from_directory(config.FRONTEND_DIR, nombre)


@app.get("/imagenes/<path:ruta>")
def imagenes_del_sitio(ruta):
    # Los logos y fotos casi no cambian: el navegador los guarda un día
    return send_from_directory(config.FRONTEND_DIR / "imagenes", ruta, max_age=86400)


@app.get("/uploads/<nombre>")
def imagenes_subidas(nombre):
    return send_from_directory(config.UPLOADS_DIR, nombre, max_age=86400)


if __name__ == "__main__":
    if not config.clave_admin_valida():
        print("AVISO: el panel de moderación está desactivado hasta que definas ADMIN_KEY en backend/.env")
    try:
        get_db().command("ping")
        print("Conectado a MongoDB.")
    except Exception as error:
        print("AVISO: no se pudo conectar a MongoDB (%s)." % type(error).__name__)
        print("       Ejecuta  python probar_conexion.py  para ver cómo arreglarlo.")
    print("Portal:  http://localhost:%d    Moderación:  http://localhost:%d/admin" % (config.PUERTO, config.PUERTO))
    app.run(host=config.HOST, port=config.PUERTO, debug=config.DEBUG)
