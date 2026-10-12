"""Pruebas automáticas del servidor.

Ejecutar desde la carpeta backend:
    python -m unittest discover -s tests -v

Usan una base de datos FALSA en memoria (tests/fakemongo.py): nunca tocan tu
base real de MongoDB Atlas ni tus archivos subidos.
"""
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "tests"))

CLAVE = "clave-de-prueba-123456"
UPLOADS = tempfile.mkdtemp(prefix="ecci_uploads_prueba_")

# Estas variables deben fijarse ANTES de importar el servidor
os.environ.update(
    {
        "MONGODB_URI": "mongodb://prueba",
        "DB_NAME": "ecci_prueba",
        "ADMIN_KEY": CLAVE,
        "UPLOADS_DIR": UPLOADS,
        "DOMINIOS_PERMITIDOS": "",
        "CORS_ORIGINS": "http://localhost:5500,null",
        "LIMITE_ENVIOS": "1000",
    }
)

import fakemongo  # noqa: E402

fakemongo.instalar()  # a partir de aquí, "import pymongo" usa la base falsa

import config  # noqa: E402
import main  # noqa: E402
import seed  # noqa: E402
import validaciones  # noqa: E402
from PIL import Image  # noqa: E402

DATOS_NOTICIA = {
    "autor": "Ana Prueba",
    "correo": "ana@ucr.ac.cr",
    "titulo": "Una noticia de prueba",
    "categoria": "Big Data",
    "resumen": "Resumen de la noticia de prueba.",
    "contenido": "Contenido de la noticia de prueba, suficientemente largo para validar.",
    "acepta": "on",
}


def imagen_bytes(formato="PNG", modo="RGB", tam=(40, 30), **opciones):
    destino = io.BytesIO()
    Image.new(modo, tam, "red").save(destino, formato, **opciones)
    return destino.getvalue()


class Base(unittest.TestCase):
    def setUp(self):
        self.c = main.app.test_client()
        bd = main.get_db()
        bd.noticias.docs.clear()
        bd.opiniones.docs.clear()
        bd.videos.docs.clear()
        main.limite_envios.reiniciar()
        main.limite_envios.limite = 1000
        main.limite_admin.reiniciar()
        main.limite_admin.limite = 10
        config.DOMINIOS_PERMITIDOS = []
        config.ADMIN_KEY = CLAVE
        for archivo in Path(UPLOADS).glob("*"):
            archivo.unlink()

    # --- ayudas
    def noticia(self, imagen=None, nombre_archivo="foto.png", **cambios):
        datos = dict(DATOS_NOTICIA, **cambios)
        datos = {k: v for k, v in datos.items() if v is not None}
        if imagen is not None:
            datos["imagen"] = (io.BytesIO(imagen), nombre_archivo)
        return self.c.post("/api/noticias", data=datos, content_type="multipart/form-data")

    def admin(self, metodo, ruta, **kwargs):
        return getattr(self.c, metodo)(ruta, headers={"X-Admin-Key": CLAVE}, **kwargs)

    def crear_noticia_aprobada(self, **cambios):
        respuesta = self.noticia(**cambios)
        self.assertEqual(respuesta.status_code, 201)
        id_ = respuesta.get_json()["id"]
        self.assertEqual(self.admin("post", "/api/admin/noticias/%s/aprobar" % id_).status_code, 200)
        return id_

    def opinion(self, **cambios):
        datos = {"nombre": "Luis", "tema": "Futuro laboral", "opinion": "Me parece un tema muy importante."}
        datos.update(cambios)
        return self.c.post("/api/opiniones", json=datos)

    def video(self, **cambios):
        datos = {
            "autor": "Ana Prueba",
            "correo": "ana@ucr.ac.cr",
            "enlace": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "titulo": "Un video de prueba",
            "categoria": "Charla",
            "descripcion": "Descripción corta.",
            "acepta": "on",
        }
        datos.update(cambios)
        return self.c.post("/api/videos", json=datos)


class PruebasVideos(Base):
    def test_video_nuevo_queda_pendiente_y_al_aprobarlo_se_publica(self):
        r = self.video()
        self.assertEqual(r.status_code, 201)
        id_ = r.get_json()["id"]
        self.assertEqual(self.c.get("/api/videos").get_json()["items"], [])

        pendientes = self.admin("get", "/api/admin/videos?estado=pendiente").get_json()["items"]
        self.assertEqual([v["id"] for v in pendientes], [id_])
        self.assertEqual(pendientes[0]["correo"], "ana@ucr.ac.cr")

        self.assertEqual(self.admin("post", "/api/admin/videos/%s/aprobar" % id_).status_code, 200)
        publicos = self.c.get("/api/videos").get_json()["items"]
        self.assertEqual(len(publicos), 1)
        self.assertEqual(publicos[0]["youtube_id"], "dQw4w9WgXcQ")
        self.assertNotIn("correo", publicos[0])
        self.assertEqual(set(publicos[0]), {"id", "titulo", "categoria", "descripcion", "autor", "youtube_id", "fecha"})

    def test_formatos_de_enlace_aceptados(self):
        for enlace in (
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtube.com/watch?v=dQw4w9WgXcQ&t=42s",
            "https://m.youtube.com/watch?feature=share&v=dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ?si=abc123",
            "youtu.be/dQw4w9WgXcQ",
            "https://www.youtube.com/shorts/dQw4w9WgXcQ",
            "https://www.youtube.com/embed/dQw4w9WgXcQ",
            "https://www.youtube.com/live/dQw4w9WgXcQ?feature=shared",
        ):
            with self.subTest(enlace=enlace):
                self.assertEqual(validaciones.id_de_youtube(enlace), "dQw4w9WgXcQ")

    def test_enlaces_no_validos(self):
        for enlace in (
            "",
            "hola",
            "https://vimeo.com/123456789",
            "https://youtube.com.sitio-malo.example/watch?v=dQw4w9WgXcQ",
            "https://www.youtube.com/watch?v=corto",
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ<script>",
            "javascript:alert(1)",
            "https://www.youtube.com/channel/UC1234567890",
        ):
            with self.subTest(enlace=enlace):
                self.assertIsNone(validaciones.id_de_youtube(enlace))
                self.assertEqual(self.video(enlace=enlace).status_code, 422)

    def test_validaciones(self):
        casos = [
            ("sin aceptar", {"acepta": ""}),
            ("categoría inventada", {"categoria": "Política"}),
            ("título corto", {"titulo": "Hola"}),
            ("descripción larga", {"descripcion": "x" * 301}),
            ("correo malo", {"correo": "no-es-correo"}),
        ]
        for nombre, cambios in casos:
            with self.subTest(nombre):
                self.assertEqual(self.video(**cambios).status_code, 422)
        self.assertEqual(self.video(descripcion="").status_code, 201)  # la descripción es opcional

    def test_campo_trampa_y_cuerpo_no_json(self):
        self.assertEqual(self.video(sitio_web="spam").status_code, 201)
        self.assertEqual(len(main.get_db().videos.docs), 0)
        self.assertEqual(self.c.post("/api/videos", data="hola", content_type="text/plain").status_code, 400)

    def test_rechazar_eliminar_y_resumen(self):
        id_ = self.video().get_json()["id"]
        self.assertEqual(self.admin("get", "/api/admin/resumen").get_json()["videos"],
                         {"pendiente": 1, "aprobada": 0, "rechazada": 0})
        self.admin("post", "/api/admin/videos/%s/rechazar" % id_, json={"motivo": "No es sobre IA"})
        self.assertEqual(self.c.get("/api/videos").get_json()["items"], [])
        todas = self.admin("get", "/api/admin/videos?estado=todas").get_json()["items"]
        self.assertEqual(todas[0]["motivo_rechazo"], "No es sobre IA")
        self.assertEqual(self.admin("delete", "/api/admin/videos/" + id_).status_code, 200)
        self.assertEqual(len(main.get_db().videos.docs), 0)


class PruebasNoticias(Base):
    def test_noticia_nueva_queda_pendiente_y_no_es_publica(self):
        r = self.noticia()
        self.assertEqual(r.status_code, 201)
        id_ = r.get_json()["id"]
        self.assertIn("pendiente", r.get_json()["mensaje"])

        publico = self.c.get("/api/noticias").get_json()
        self.assertEqual(publico["total"], 0)
        self.assertEqual(publico["items"], [])
        self.assertEqual(self.c.get("/api/noticias/ultima").status_code, 404)
        self.assertEqual(self.c.get("/api/noticias/" + id_).status_code, 404)

        pendientes = self.admin("get", "/api/admin/noticias?estado=pendiente").get_json()["items"]
        self.assertEqual([n["id"] for n in pendientes], [id_])
        self.assertEqual(pendientes[0]["correo"], "ana@ucr.ac.cr")  # el moderador sí lo ve

    def test_aprobar_publica_la_noticia(self):
        id_ = self.crear_noticia_aprobada()
        self.assertEqual(self.c.get("/api/noticias").get_json()["total"], 1)
        ultima = self.c.get("/api/noticias/ultima").get_json()
        self.assertEqual(ultima["id"], id_)
        self.assertIn("Contenido de la noticia", ultima["contenido"])
        self.assertIsNotNone(ultima["fecha"])
        self.assertEqual(self.c.get("/api/noticias/" + id_).status_code, 200)

    def test_el_correo_nunca_sale_en_la_api_publica(self):
        id_ = self.crear_noticia_aprobada()
        for ruta in ("/api/noticias", "/api/noticias/ultima", "/api/noticias/" + id_, "/api/noticias/aleatorias"):
            with self.subTest(ruta=ruta):
                self.assertNotIn("ana@ucr.ac.cr", self.c.get(ruta).get_data(as_text=True))

    def test_rechazar_la_oculta_y_guarda_el_motivo(self):
        id_ = self.noticia().get_json()["id"]
        r = self.admin("post", "/api/admin/noticias/%s/rechazar" % id_, json={"motivo": "Sin fuentes"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.c.get("/api/noticias").get_json()["total"], 0)
        rechazadas = self.admin("get", "/api/admin/noticias?estado=rechazada").get_json()["items"]
        self.assertEqual(rechazadas[0]["motivo_rechazo"], "Sin fuentes")

    def test_rechazar_una_noticia_aprobada_la_despublica(self):
        id_ = self.crear_noticia_aprobada()
        self.admin("post", "/api/admin/noticias/%s/rechazar" % id_, json={})
        self.assertEqual(self.c.get("/api/noticias/" + id_).status_code, 404)
        self.assertEqual(self.c.get("/api/noticias").get_json()["total"], 0)

    def test_aprobar_dos_veces_no_cambia_la_fecha_de_publicacion(self):
        id_ = self.crear_noticia_aprobada()
        antes = self.c.get("/api/noticias/" + id_).get_json()["fecha"]
        self.admin("post", "/api/admin/noticias/%s/aprobar" % id_)
        self.assertEqual(self.c.get("/api/noticias/" + id_).get_json()["fecha"], antes)

    def test_validaciones_rechazan_datos_malos(self):
        casos = [
            ("titulo vacío", {"titulo": ""}),
            ("titulo muy corto", {"titulo": "abc"}),
            ("titulo muy largo", {"titulo": "x" * 121}),
            ("categoría inventada", {"categoria": "Hackeo"}),
            ("correo inválido", {"correo": "no-es-un-correo"}),
            ("sin aceptar", {"acepta": None}),
            ("resumen muy largo", {"resumen": "x" * 201}),
            ("contenido muy corto", {"contenido": "corto"}),
            ("autor vacío", {"autor": "   "}),
        ]
        for nombre, cambios in casos:
            with self.subTest(nombre):
                r = self.noticia(**cambios)
                self.assertEqual(r.status_code, 422)
                self.assertTrue(r.get_json()["detail"])
        self.assertEqual(len(main.get_db().noticias.docs), 0)

    def test_dominios_permitidos(self):
        config.DOMINIOS_PERMITIDOS = ["ucr.ac.cr"]
        self.assertEqual(self.noticia(correo="x@gmail.com").status_code, 422)
        self.assertEqual(self.noticia(correo="x@evilucr.ac.cr").status_code, 422)
        self.assertEqual(self.noticia(correo="x@ucr.ac.cr").status_code, 201)
        self.assertEqual(self.noticia(correo="x@ecci.ucr.ac.cr").status_code, 201)

    def test_campo_trampa_para_bots(self):
        r = self.noticia(sitio_web="http://spam.example")
        self.assertEqual(r.status_code, 201)  # el bot cree que funcionó...
        self.assertEqual(len(main.get_db().noticias.docs), 0)  # ...pero no se guardó nada

    def test_orden_paginacion_y_total(self):
        a = self.crear_noticia_aprobada(titulo="Noticia A")
        b = self.crear_noticia_aprobada(titulo="Noticia B")
        c = self.crear_noticia_aprobada(titulo="Noticia C")
        todas = self.c.get("/api/noticias").get_json()
        self.assertEqual([n["id"] for n in todas["items"]], [c, b, a])
        self.assertEqual(todas["total"], 3)
        pagina2 = self.c.get("/api/noticias?limite=2&pagina=2").get_json()
        self.assertEqual([n["id"] for n in pagina2["items"]], [a])
        self.assertEqual(self.c.get("/api/noticias?limite=abc&pagina=-4").status_code, 200)

    def test_noticias_aleatorias_solo_aprobadas(self):
        aprobadas = {self.crear_noticia_aprobada(titulo="Aprobada número %d" % i) for i in range(5)}
        pendientes = {self.noticia(titulo="Pendiente número %d" % i).get_json()["id"] for i in range(2)}
        r = self.c.get("/api/noticias/aleatorias?n=3").get_json()
        ids = [n["id"] for n in r]
        self.assertEqual(len(ids), 3)
        self.assertEqual(len(set(ids)), 3)
        self.assertTrue(set(ids) <= aprobadas)
        self.assertFalse(set(ids) & pendientes)
        self.assertEqual(len(self.c.get("/api/noticias/aleatorias?n=50").get_json()), 5)

    def test_id_invalido_o_inexistente_da_404(self):
        self.assertEqual(self.c.get("/api/noticias/xyz").status_code, 404)
        self.assertEqual(self.c.get("/api/noticias/" + "a" * 24).status_code, 404)

    def test_texto_peligroso_se_guarda_como_texto_plano(self):
        peligro = "<img src=x onerror=alert(1)>"
        self.crear_noticia_aprobada(titulo=peligro)
        r = self.c.get("/api/noticias/ultima")
        self.assertTrue(r.content_type.startswith("application/json"))
        self.assertEqual(r.get_json()["titulo"], peligro)  # la página lo escapa al mostrarlo
        self.assertEqual(r.headers["X-Content-Type-Options"], "nosniff")


class PruebasImagenes(Base):
    def imagen_guardada(self, respuesta):
        id_ = respuesta.get_json()["id"]
        noticias = self.admin("get", "/api/admin/noticias?estado=todas").get_json()["items"]
        return next(n for n in noticias if n["id"] == id_)["imagen_url"]

    def test_imagen_valida_se_guarda_como_jpeg_y_se_sirve(self):
        r = self.noticia(imagen=imagen_bytes("PNG"))
        self.assertEqual(r.status_code, 201)
        url = self.imagen_guardada(r)
        self.assertTrue(url.startswith("/uploads/") and url.endswith(".jpg"))
        servida = self.c.get(url)
        self.assertEqual(servida.status_code, 200)
        self.assertEqual(servida.content_type, "image/jpeg")
        self.assertEqual(Image.open(io.BytesIO(servida.data)).format, "JPEG")

    def test_imagen_se_reduce_a_1600_px(self):
        r = self.noticia(imagen=imagen_bytes("PNG", tam=(3200, 1000)))
        ruta = Path(UPLOADS) / Path(self.imagen_guardada(r)).name
        self.assertEqual(max(Image.open(ruta).size), 1600)

    def test_se_eliminan_los_metadatos_de_la_foto(self):
        exif = Image.Exif()
        exif[0x010F] = "CamaraSecreta"  # fabricante de la cámara
        r = self.noticia(imagen=imagen_bytes("JPEG", exif=exif), nombre_archivo="foto.jpg")
        self.assertEqual(r.status_code, 201)
        ruta = Path(UPLOADS) / Path(self.imagen_guardada(r)).name
        self.assertNotIn(0x010F, Image.open(ruta).getexif())

    def test_png_con_transparencia_es_aceptado(self):
        self.assertEqual(self.noticia(imagen=imagen_bytes("PNG", modo="RGBA")).status_code, 201)

    def test_archivo_falso_con_extension_de_imagen_se_rechaza(self):
        r = self.noticia(imagen=b"esto no es una imagen, es un texto", nombre_archivo="virus.png")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(len(main.get_db().noticias.docs), 0)
        self.assertEqual(list(Path(UPLOADS).glob("*")), [])

    def test_formato_no_permitido_se_rechaza(self):
        self.assertEqual(self.noticia(imagen=imagen_bytes("GIF"), nombre_archivo="a.gif").status_code, 400)

    def test_imagen_de_mas_de_5mb_se_rechaza(self):
        r = self.noticia(imagen=b"\0" * (5 * 1024 * 1024 + 1))
        self.assertEqual(r.status_code, 413)
        self.assertEqual(len(main.get_db().noticias.docs), 0)

    def test_envio_gigante_se_rechaza(self):
        self.assertEqual(self.noticia(imagen=b"\0" * (7 * 1024 * 1024)).status_code, 413)

    def test_noticia_sin_imagen_es_valida(self):
        r = self.noticia()
        self.assertIsNone(self.imagen_guardada(r))

    def test_datos_invalidos_no_dejan_imagenes_huerfanas(self):
        self.noticia(imagen=imagen_bytes("PNG"), titulo="")
        self.assertEqual(list(Path(UPLOADS).glob("*")), [])


class PruebasOpiniones(Base):
    def test_flujo_completo(self):
        r = self.opinion()
        self.assertEqual(r.status_code, 201)
        id_ = r.get_json()["id"]
        self.assertEqual(self.c.get("/api/opiniones").get_json()["items"], [])

        pendientes = self.admin("get", "/api/admin/opiniones").get_json()["items"]
        self.assertEqual([o["id"] for o in pendientes], [id_])

        self.assertEqual(self.admin("post", "/api/admin/opiniones/%s/aprobar" % id_).status_code, 200)
        publicas = self.c.get("/api/opiniones").get_json()["items"]
        self.assertEqual(len(publicas), 1)
        self.assertEqual(set(publicas[0]), {"id", "nombre", "tema", "texto", "fecha"})

    def test_rechazar_y_eliminar(self):
        id_ = self.opinion().get_json()["id"]
        self.admin("post", "/api/admin/opiniones/%s/rechazar" % id_, json={"motivo": "Ofensiva"})
        self.assertEqual(self.c.get("/api/opiniones").get_json()["items"], [])
        self.assertEqual(self.admin("delete", "/api/admin/opiniones/" + id_).status_code, 200)
        self.assertEqual(len(main.get_db().opiniones.docs), 0)

    def test_validaciones(self):
        casos = [
            ("tema inventado", {"tema": "Política"}),
            ("opinión muy corta", {"opinion": "ok"}),
            ("opinión muy larga", {"opinion": "x" * 1001}),
            ("nombre vacío", {"nombre": ""}),
        ]
        for nombre, cambios in casos:
            with self.subTest(nombre):
                self.assertEqual(self.opinion(**cambios).status_code, 422)

    def test_cuerpo_que_no_es_json_se_rechaza(self):
        r = self.c.post("/api/opiniones", data="hola", content_type="text/plain")
        self.assertEqual(r.status_code, 400)
        r = self.c.post("/api/opiniones", data="[1, 2]", content_type="application/json")
        self.assertEqual(r.status_code, 400)

    def test_campo_trampa(self):
        self.assertEqual(self.opinion(sitio_web="spam").status_code, 201)
        self.assertEqual(len(main.get_db().opiniones.docs), 0)

    def test_orden_mas_reciente_primero(self):
        ids = []
        for i in range(3):
            id_ = self.opinion(opinion="Opinión número %d del foro" % i).get_json()["id"]
            self.admin("post", "/api/admin/opiniones/%s/aprobar" % id_)
            ids.append(id_)
        publicas = self.c.get("/api/opiniones").get_json()["items"]
        self.assertEqual([o["id"] for o in publicas], ids[::-1])


class PruebasAdmin(Base):
    def test_sin_clave_o_con_clave_incorrecta_no_entra(self):
        self.assertEqual(self.c.get("/api/admin/resumen").status_code, 401)
        r = self.c.get("/api/admin/resumen", headers={"X-Admin-Key": "otra-clave-cualquiera"})
        self.assertEqual(r.status_code, 401)
        self.assertEqual(self.admin("get", "/api/admin/resumen").status_code, 200)

    def test_acciones_sin_clave_no_hacen_nada(self):
        id_ = self.noticia().get_json()["id"]
        self.assertEqual(self.c.post("/api/admin/noticias/%s/aprobar" % id_).status_code, 401)
        self.assertEqual(self.c.delete("/api/admin/noticias/" + id_).status_code, 401)
        self.assertEqual(self.c.get("/api/noticias").get_json()["total"], 0)
        self.assertEqual(len(main.get_db().noticias.docs), 1)

    def test_panel_desactivado_con_clave_debil_o_de_ejemplo(self):
        for clave in ("", "corta", config.CLAVE_EJEMPLO):
            with self.subTest(clave=clave):
                config.ADMIN_KEY = clave
                r = self.c.get("/api/admin/resumen", headers={"X-Admin-Key": clave})
                self.assertEqual(r.status_code, 503)

    def test_bloqueo_tras_varios_intentos_fallidos(self):
        main.limite_admin.limite = 3
        for _ in range(3):
            self.assertEqual(self.c.get("/api/admin/resumen", headers={"X-Admin-Key": "mala"}).status_code, 401)
        self.assertEqual(self.admin("get", "/api/admin/resumen").status_code, 429)

    def test_resumen_cuenta_por_estado(self):
        self.crear_noticia_aprobada()
        self.noticia()
        self.opinion()
        resumen = self.admin("get", "/api/admin/resumen").get_json()
        self.assertEqual(resumen["noticias"], {"pendiente": 1, "aprobada": 1, "rechazada": 0})
        self.assertEqual(resumen["opiniones"], {"pendiente": 1, "aprobada": 0, "rechazada": 0})

    def test_parametros_invalidos(self):
        self.assertEqual(self.admin("get", "/api/admin/noticias?estado=borrada").status_code, 422)
        self.assertEqual(self.admin("get", "/api/admin/usuarios").status_code, 404)
        self.assertEqual(self.admin("post", "/api/admin/noticias/zzz/aprobar").status_code, 404)
        self.assertEqual(self.admin("post", "/api/admin/noticias/%s/aprobar" % ("b" * 24)).status_code, 404)

    def test_motivo_de_rechazo_muy_largo(self):
        id_ = self.noticia().get_json()["id"]
        r = self.admin("post", "/api/admin/noticias/%s/rechazar" % id_, json={"motivo": "x" * 301})
        self.assertEqual(r.status_code, 422)

    def test_eliminar_noticia_borra_tambien_su_imagen(self):
        r = self.noticia(imagen=imagen_bytes("PNG"))
        id_ = r.get_json()["id"]
        archivos = list(Path(UPLOADS).glob("*.jpg"))
        self.assertEqual(len(archivos), 1)
        self.assertEqual(self.admin("delete", "/api/admin/noticias/" + id_).status_code, 200)
        self.assertEqual(list(Path(UPLOADS).glob("*.jpg")), [])
        self.assertEqual(len(main.get_db().noticias.docs), 0)

    def test_respuestas_del_panel_no_se_guardan_en_cache(self):
        self.assertEqual(self.admin("get", "/api/admin/resumen").headers["Cache-Control"], "no-store")

    def test_eliminar_no_borra_imagenes_del_sitio(self):
        # Una noticia de ejemplo apunta a imagenes/robot-ia.jpg: eso no se debe tocar
        doc = {"titulo": "x", "estado": "aprobada", "imagen_url": "imagenes/robot-ia.jpg"}
        id_ = str(main.get_db().noticias.insert_one(doc).inserted_id)
        self.assertEqual(self.admin("delete", "/api/admin/noticias/" + id_).status_code, 200)
        self.assertTrue((config.FRONTEND_DIR / "imagenes" / "robot-ia.jpg").exists())


class PruebasCloudinary(Base):
    """Con CLOUDINARY_URL definida las imágenes van a la nube (aquí simulada, sin internet)."""

    def setUp(self):
        super().setUp()
        import imagenes
        self.imagenes = imagenes
        self.llamadas = []
        self.original = (imagenes._llamar_cloudinary, config.CLOUDINARY_CLOUD,
                         config.CLOUDINARY_KEY, config.CLOUDINARY_SECRET)
        config.CLOUDINARY_CLOUD, config.CLOUDINARY_KEY, config.CLOUDINARY_SECRET = "nube-prueba", "123", "secreto"

        def falsa(accion, parametros, archivo=None):
            self.llamadas.append((accion, parametros, archivo))
            return {"secure_url": "https://res.cloudinary.com/nube-prueba/image/upload/v1/%s/%s.jpg"
                    % (parametros.get("folder"), parametros.get("public_id"))}

        imagenes._llamar_cloudinary = falsa

    def tearDown(self):
        (self.imagenes._llamar_cloudinary, config.CLOUDINARY_CLOUD,
         config.CLOUDINARY_KEY, config.CLOUDINARY_SECRET) = self.original
        super().tearDown()

    def test_imagen_se_sube_a_la_nube_y_no_al_disco(self):
        r = self.noticia(imagen=imagen_bytes("PNG"))
        self.assertEqual(r.status_code, 201)
        accion, parametros, archivo = self.llamadas[0]
        self.assertEqual((accion, parametros["folder"]), ("upload", "ecci-ia"))
        self.assertEqual(Image.open(io.BytesIO(archivo)).format, "JPEG")  # se limpia antes de subir
        self.assertEqual(list(Path(UPLOADS).glob("*.jpg")), [])
        doc = main.get_db().noticias.docs[0]
        self.assertTrue(doc["imagen_url"].startswith("https://res.cloudinary.com/nube-prueba/"))

    def test_eliminar_noticia_borra_la_imagen_de_la_nube(self):
        id_ = self.noticia(imagen=imagen_bytes("PNG")).get_json()["id"]
        public_id = "ecci-ia/" + self.llamadas[0][1]["public_id"]
        self.assertEqual(self.admin("delete", "/api/admin/noticias/" + id_).status_code, 200)
        self.assertEqual(self.llamadas[-1][:2], ("destroy", {"public_id": public_id}))

    def test_firma_coincide_con_el_formato_de_cloudinary(self):
        import hashlib
        esperado = hashlib.sha1(b"folder=ecci-ia&timestamp=100secreto").hexdigest()
        self.assertEqual(self.imagenes._firmar({"timestamp": "100", "folder": "ecci-ia"}), esperado)


class PruebasSeguridadYArchivos(Base):
    def test_limite_de_envios_por_persona(self):
        main.limite_envios.limite = 2
        codigos = [self.noticia(titulo="Noticia número %d" % i).status_code for i in range(3)]
        self.assertEqual(codigos, [201, 201, 429])
        # las opiniones tienen su propio contador
        self.assertEqual(self.opinion().status_code, 201)

    def test_cors_solo_para_origenes_permitidos(self):
        permitido = self.c.get("/api/salud", headers={"Origin": "http://localhost:5500"})
        self.assertEqual(permitido.headers.get("Access-Control-Allow-Origin"), "http://localhost:5500")
        archivo_local = self.c.get("/api/salud", headers={"Origin": "null"})
        self.assertEqual(archivo_local.headers.get("Access-Control-Allow-Origin"), "null")
        ajeno = self.c.get("/api/salud", headers={"Origin": "http://sitio-malo.example"})
        self.assertNotIn("Access-Control-Allow-Origin", ajeno.headers)

    def test_preflight_cors(self):
        r = self.c.open(
            "/api/noticias",
            method="OPTIONS",
            headers={"Origin": "http://localhost:5500", "Access-Control-Request-Method": "POST"},
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.headers["Access-Control-Allow-Origin"], "http://localhost:5500")
        self.assertIn("X-Admin-Key", r.headers["Access-Control-Allow-Headers"])

    def test_cabeceras_de_seguridad(self):
        r = self.c.get("/api/salud")
        self.assertEqual(r.headers["X-Frame-Options"], "DENY")
        self.assertEqual(r.headers["X-Content-Type-Options"], "nosniff")

    def test_salud(self):
        self.assertEqual(self.c.get("/api/salud").get_json(), {"ok": True, "base_de_datos": True})

    def test_paginas_publicas(self):
        for ruta, texto in (("/", "ECCI"), ("/admin", "moderación"), ("/styles.css", "--azul-ucr"),
                            ("/extra.css", ".mensaje"), ("/app.js", "ECCI")):
            with self.subTest(ruta=ruta):
                r = self.c.get(ruta)
                self.assertEqual(r.status_code, 200)
                self.assertIn(texto, r.get_data(as_text=True))
        self.assertEqual(self.c.get("/imagenes/logo-ecci.jpg").status_code, 200)

    def test_no_se_exponen_archivos_del_servidor(self):
        for ruta in ("/main.py", "/config.py", "/.env", "/backend/.env", "/backend/main.py",
                     "/requirements.txt", "/seed.py", "/imagenes/../backend/config.py",
                     "/imagenes/..%2fbackend%2fconfig.py", "/uploads/..%2fconfig.py", "/uploads/inexistente.jpg"):
            with self.subTest(ruta=ruta):
                self.assertEqual(self.c.get(ruta).status_code, 404)

    def test_base_de_datos_caida_responde_503(self):
        original = main.get_db

        class BaseRota:
            def __getattr__(self, nombre):
                raise fakemongo.PyMongoError("caída")

        try:
            main.get_db = lambda: BaseRota()
            self.assertEqual(self.c.get("/api/noticias").status_code, 503)
            main.get_db = lambda: (_ for _ in ()).throw(RuntimeError("Falta MONGODB_URI"))
            r = self.c.get("/api/noticias")
            self.assertEqual(r.status_code, 503)
            self.assertIn("MONGODB_URI", r.get_json()["detail"])
        finally:
            main.get_db = original

    def test_metodo_no_permitido_responde_json(self):
        r = self.c.put("/api/noticias")
        self.assertEqual(r.status_code, 405)
        self.assertIn("detail", r.get_json())


class PruebasValidacionesYSemilla(unittest.TestCase):
    def test_los_ejemplos_cumplen_las_mismas_reglas_que_los_formularios(self):
        bd = fakemongo.BaseDeDatos()
        self.assertEqual(seed.sembrar(bd), (len(seed.NOTICIAS), len(seed.OPINIONES)))
        for n in bd.noticias.docs:
            with self.subTest(titulo=n["titulo"]):
                validaciones.validar_noticia(dict(n, acepta="on"))
        for o in bd.opiniones.docs:
            with self.subTest(nombre=o["nombre"]):
                validaciones.validar_opinion({"nombre": o["nombre"], "tema": o["tema"], "opinion": o["texto"]})

    def test_la_imagen_de_los_ejemplos_existe(self):
        for fila in seed.NOTICIAS:
            imagen = fila[5]
            if imagen:
                self.assertTrue((config.FRONTEND_DIR / imagen).exists(), imagen)

    def test_sembrar_no_duplica_y_forzar_solo_reemplaza_ejemplos(self):
        bd = fakemongo.BaseDeDatos()
        seed.sembrar(bd)
        self.assertIsNone(seed.sembrar(bd))
        bd.noticias.insert_one({"titulo": "Mía", "estado": "pendiente"})  # escrita por una persona real
        seed.sembrar(bd, forzar=True)
        self.assertEqual(bd.noticias.count_documents({}), len(seed.NOTICIAS) + 1)
        self.assertEqual(bd.noticias.count_documents({"titulo": "Mía"}), 1)

    def test_limpieza_de_texto(self):
        self.assertEqual(validaciones.limpiar("  hola\x00 mundo\x07  "), "hola mundo")
        self.assertEqual(validaciones.limpiar(None), "")


if __name__ == "__main__":
    unittest.main()
