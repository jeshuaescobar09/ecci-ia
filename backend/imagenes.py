"""Subida segura de imágenes.

Cada imagen se verifica con Pillow, se reduce a un máximo de 1600 px y se vuelve
a guardar como JPEG con un nombre aleatorio. Al re-guardarla se eliminan los
metadatos (por ejemplo, la ubicación GPS de la foto) y cualquier contenido
que no sea una imagen real.

Dónde se guarda:
- Si CLOUDINARY_URL está definida (en Render), se sube a Cloudinary y en la base
  de datos se guarda su dirección https://res.cloudinary.com/...
- Si no (en tu PC), se guarda en backend/uploads y se guarda /uploads/archivo.jpg.
"""
import hashlib
import io
import json
import re
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

from PIL import Image

import config

# Evita "bombas de descompresión": imágenes pequeñas en bytes pero gigantes en píxeles
Image.MAX_IMAGE_PIXELS = 40_000_000

FORMATOS_PERMITIDOS = {"JPEG", "PNG", "WEBP"}
_NOMBRE_VALIDO = re.compile(r"^[0-9a-f]{32}\.jpg$")
CARPETA_NUBE = "ecci-ia"


class ErrorImagen(Exception):
    def __init__(self, estado, mensaje):
        super().__init__(mensaje)
        self.estado = estado
        self.mensaje = mensaje


def _limpiar(datos):
    """Verifica que sea una imagen real y la devuelve como JPEG limpio (bytes)."""
    try:
        with Image.open(io.BytesIO(datos)) as prueba:
            formato = prueba.format
            prueba.verify()
        if formato not in FORMATOS_PERMITIDOS:
            raise ValueError("formato no permitido")

        img = Image.open(io.BytesIO(datos))
        img.load()
        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            rgba = img.convert("RGBA")
            fondo = Image.new("RGB", rgba.size, (255, 255, 255))
            fondo.paste(rgba, mask=rgba.split()[-1])
            img = fondo
        else:
            img = img.convert("RGB")
        img.thumbnail((1600, 1600))

        salida = io.BytesIO()
        img.save(salida, "JPEG", quality=85, optimize=True)
        return salida.getvalue()
    except Exception:
        raise ErrorImagen(400, "El archivo no es una imagen válida (usa JPG, PNG o WEBP).")


# ---------- Cloudinary (sin librerías extra: su API es un simple POST) ----------

def _firmar(parametros):
    """Firma que pide Cloudinary: sha1 de los parámetros ordenados + el secreto."""
    texto = "&".join("%s=%s" % (k, parametros[k]) for k in sorted(parametros))
    return hashlib.sha1((texto + config.CLOUDINARY_SECRET).encode()).hexdigest()


def _llamar_cloudinary(accion, parametros, archivo=None):
    parametros = dict(parametros, timestamp=str(int(time.time())))
    campos = dict(parametros, api_key=config.CLOUDINARY_KEY, signature=_firmar(parametros))

    limite = "----ecci" + uuid.uuid4().hex
    cuerpo = io.BytesIO()
    for nombre, valor in campos.items():
        cuerpo.write(('--%s\r\nContent-Disposition: form-data; name="%s"\r\n\r\n%s\r\n'
                      % (limite, nombre, valor)).encode())
    if archivo is not None:
        cuerpo.write(('--%s\r\nContent-Disposition: form-data; name="file"; filename="foto.jpg"\r\n'
                      'Content-Type: image/jpeg\r\n\r\n' % limite).encode())
        cuerpo.write(archivo)
        cuerpo.write(b"\r\n")
    cuerpo.write(("--%s--\r\n" % limite).encode())

    url = "https://api.cloudinary.com/v1_1/%s/image/%s" % (config.CLOUDINARY_CLOUD, accion)
    pedido = urllib.request.Request(url, data=cuerpo.getvalue(), method="POST")
    pedido.add_header("Content-Type", "multipart/form-data; boundary=" + limite)
    with urllib.request.urlopen(pedido, timeout=30) as resp:
        return json.loads(resp.read().decode())


def _prefijo_nube():
    return "https://res.cloudinary.com/%s/image/upload/" % config.CLOUDINARY_CLOUD


# ---------- Funciones que usa main.py ----------

def guardar_imagen(archivo):
    """archivo: objeto FileStorage de Flask. Devuelve la dirección pública de la imagen."""
    maximo = config.MAX_IMAGEN_MB * 1024 * 1024
    datos = archivo.stream.read(maximo + 1)
    if len(datos) > maximo:
        raise ErrorImagen(413, "La imagen supera los %d MB." % config.MAX_IMAGEN_MB)

    jpeg = _limpiar(datos)
    nombre = uuid.uuid4().hex

    if config.usa_cloudinary():
        try:
            r = _llamar_cloudinary("upload", {"folder": CARPETA_NUBE, "public_id": nombre}, jpeg)
            return r["secure_url"]
        except (urllib.error.URLError, OSError, KeyError, ValueError):
            raise ErrorImagen(502, "No se pudo guardar la imagen. Intenta de nuevo en un momento.")

    config.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    (config.UPLOADS_DIR / (nombre + ".jpg")).write_bytes(jpeg)
    return "/uploads/" + nombre + ".jpg"


def borrar_imagen(url):
    """Borra una imagen subida por el portal. Ignora cualquier otra ruta."""
    if not url:
        return

    if config.usa_cloudinary() and url.startswith(_prefijo_nube()):
        coincide = re.search(r"/%s/([0-9a-f]{32})\.jpg$" % CARPETA_NUBE, url)
        if coincide:
            try:
                _llamar_cloudinary("destroy", {"public_id": CARPETA_NUBE + "/" + coincide.group(1)})
            except (urllib.error.URLError, OSError, ValueError):
                pass  # si falla, la imagen queda en la nube pero la noticia sí se borra
        return

    if not url.startswith("/uploads/"):
        return
    nombre = Path(url).name
    if not _NOMBRE_VALIDO.match(nombre):
        return
    try:
        (config.UPLOADS_DIR / nombre).unlink()
    except FileNotFoundError:
        pass
