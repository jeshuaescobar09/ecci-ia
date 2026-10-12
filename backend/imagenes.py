"""Subida segura de imágenes.

Cada imagen se verifica con Pillow, se reduce a un máximo de 1600 px y se vuelve
a guardar como JPEG con un nombre aleatorio. Al re-guardarla se eliminan los
metadatos (por ejemplo, la ubicación GPS de la foto) y cualquier contenido
que no sea una imagen real.

En la base de datos solo se guarda la dirección (/uploads/archivo.jpg).
Para publicar el portal en internet, cambia este módulo para subir a Cloudinary
o a un almacenamiento tipo S3 y guarda esa URL en lugar de la local.
"""
import io
import re
import uuid
from pathlib import Path

from PIL import Image

import config

# Evita "bombas de descompresión": imágenes pequeñas en bytes pero gigantes en píxeles
Image.MAX_IMAGE_PIXELS = 40_000_000

FORMATOS_PERMITIDOS = {"JPEG", "PNG", "WEBP"}
_NOMBRE_VALIDO = re.compile(r"^[0-9a-f]{32}\.jpg$")


class ErrorImagen(Exception):
    def __init__(self, estado, mensaje):
        super().__init__(mensaje)
        self.estado = estado
        self.mensaje = mensaje


def guardar_imagen(archivo):
    """archivo: objeto FileStorage de Flask. Devuelve la ruta pública (/uploads/xxx.jpg)."""
    maximo = config.MAX_IMAGEN_MB * 1024 * 1024
    datos = archivo.stream.read(maximo + 1)
    if len(datos) > maximo:
        raise ErrorImagen(413, "La imagen supera los %d MB." % config.MAX_IMAGEN_MB)

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

        config.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        nombre = uuid.uuid4().hex + ".jpg"
        img.save(config.UPLOADS_DIR / nombre, "JPEG", quality=85, optimize=True)
    except Exception:
        raise ErrorImagen(400, "El archivo no es una imagen válida (usa JPG, PNG o WEBP).")

    return "/uploads/" + nombre


def borrar_imagen(url):
    """Borra una imagen subida por el portal. Ignora cualquier otra ruta."""
    if not url or not url.startswith("/uploads/"):
        return
    nombre = Path(url).name
    if not _NOMBRE_VALIDO.match(nombre):
        return
    try:
        (config.UPLOADS_DIR / nombre).unlink()
    except FileNotFoundError:
        pass
