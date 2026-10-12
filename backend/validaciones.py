"""Validación y limpieza de los textos que escribe la gente.

Estas funciones no dependen de Flask ni de MongoDB: reciben un diccionario
(o request.form) y devuelven datos limpios o lanzan ErrorValidacion con un
mensaje en español que se muestra tal cual en la página.
"""
import re
from urllib.parse import parse_qs, urlparse

import config


class ErrorValidacion(Exception):
    def __init__(self, mensaje):
        super().__init__(mensaje)
        self.mensaje = mensaje


# Caracteres de control (menos salto de línea y tabulador)
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def limpiar(valor):
    if valor is None:
        return ""
    return _CONTROL.sub("", str(valor)).strip()


def _texto(valor, nombre, minimo, maximo):
    v = limpiar(valor)
    if not v:
        raise ErrorValidacion("Falta el campo «%s»." % nombre)
    if len(v) < minimo:
        raise ErrorValidacion("«%s» es muy corto (mínimo %d caracteres)." % (nombre, minimo))
    if len(v) > maximo:
        raise ErrorValidacion("«%s» es muy largo (máximo %d caracteres)." % (nombre, maximo))
    return v


def validar_correo(valor):
    v = limpiar(valor).lower()
    if not v:
        raise ErrorValidacion("Falta el campo «Correo institucional».")
    if len(v) > 254 or not _CORREO.match(v):
        raise ErrorValidacion("El correo no tiene un formato válido.")
    if config.DOMINIOS_PERMITIDOS:
        dominio = v.rsplit("@", 1)[1]
        if not any(dominio == d or dominio.endswith("." + d) for d in config.DOMINIOS_PERMITIDOS):
            raise ErrorValidacion(
                "Usa tu correo institucional (%s)."
                % ", ".join("@" + d for d in config.DOMINIOS_PERMITIDOS)
            )
    return v


def _de_lista(valor, nombre, permitidos):
    v = limpiar(valor)
    if v not in permitidos:
        raise ErrorValidacion("Elige un valor válido en «%s»." % nombre)
    return v


def validar_noticia(campos):
    """campos: request.form o un diccionario con los datos del formulario."""
    if not limpiar(campos.get("acepta")):
        raise ErrorValidacion("Debes confirmar que la información es veraz.")
    return {
        "autor": _texto(campos.get("autor"), "Nombre del autor", 2, 80),
        "correo": validar_correo(campos.get("correo")),
        "titulo": _texto(campos.get("titulo"), "Título de la noticia", 5, 120),
        "categoria": _de_lista(campos.get("categoria"), "Categoría", config.CATEGORIAS),
        "resumen": _texto(campos.get("resumen"), "Resumen", 10, 200),
        "contenido": _texto(campos.get("contenido"), "Contenido", 30, 10000),
    }


_ID_YOUTUBE = re.compile(r"^[A-Za-z0-9_-]{11}$")
_DOMINIOS_YOUTUBE = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com", "youtube-nocookie.com",
                     "www.youtube-nocookie.com"}


def id_de_youtube(enlace):
    """Saca el identificador de 11 caracteres de un enlace de YouTube, o None si no es válido.

    Acepta: youtube.com/watch?v=ID, youtu.be/ID, youtube.com/shorts/ID, /embed/ID y /live/ID.
    """
    v = limpiar(enlace)
    if not v or len(v) > 300:
        return None
    if "://" not in v:
        v = "https://" + v
    try:
        partes = urlparse(v)
    except ValueError:
        return None
    if partes.scheme not in ("http", "https"):
        return None
    dominio = (partes.hostname or "").lower()
    trozos = [t for t in partes.path.split("/") if t]

    candidato = None
    if dominio in ("youtu.be", "www.youtu.be"):
        candidato = trozos[0] if trozos else None
    elif dominio in _DOMINIOS_YOUTUBE:
        if partes.path == "/watch":
            candidato = (parse_qs(partes.query).get("v") or [None])[0]
        elif len(trozos) >= 2 and trozos[0] in ("shorts", "embed", "live", "v"):
            candidato = trozos[1]
    if candidato and _ID_YOUTUBE.match(candidato):
        return candidato
    return None


def validar_video(campos):
    if not limpiar(campos.get("acepta")):
        raise ErrorValidacion("Debes confirmar que tienes permiso para compartir el video.")
    youtube_id = id_de_youtube(campos.get("enlace"))
    if not youtube_id:
        raise ErrorValidacion(
            "El enlace no es un video de YouTube válido. Cópialo desde el botón «Compartir» de YouTube."
        )
    descripcion = limpiar(campos.get("descripcion"))
    if len(descripcion) > 300:
        raise ErrorValidacion("«Descripción» es muy larga (máximo 300 caracteres).")
    return {
        "autor": _texto(campos.get("autor"), "Nombre del autor", 2, 80),
        "correo": validar_correo(campos.get("correo")),
        "titulo": _texto(campos.get("titulo"), "Título del video", 5, 120),
        "categoria": _de_lista(campos.get("categoria"), "Categoría", config.CATEGORIAS_VIDEO),
        "descripcion": descripcion,
        "youtube_id": youtube_id,
    }


def validar_opinion(campos):
    return {
        "nombre": _texto(campos.get("nombre"), "Nombre", 2, 40),
        "tema": _de_lista(campos.get("tema"), "Tema", config.TEMAS_OPINION),
        "texto": _texto(campos.get("opinion"), "Tu opinión", 5, 1000),
    }
