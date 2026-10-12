"""Conexión con MongoDB Atlas (PyMongo).

Colecciones que usa el portal:
  noticias  -> titulo, resumen, contenido, categoria, autor, correo, imagen_url,
               estado (pendiente | aprobada | rechazada), motivo_rechazo,
               fecha_creacion, fecha_publicacion
  opiniones -> nombre, tema, texto, estado, motivo_rechazo,
               fecha_creacion, fecha_publicacion
  videos    -> titulo, descripcion, categoria, autor, correo, youtube_id,
               estado, motivo_rechazo, fecha_creacion, fecha_publicacion
"""
import certifi
from pymongo import MongoClient

import config

_cliente = None
_indices_listos = False


def get_db():
    """Devuelve la base de datos; crea la conexión la primera vez."""
    global _cliente, _indices_listos

    if _cliente is None:
        if not config.MONGODB_URI:
            raise RuntimeError(
                "Falta MONGODB_URI. Copia backend/.env.example a backend/.env "
                "y pega tu cadena de conexión de MongoDB Atlas."
            )
        opciones = {"serverSelectionTimeoutMS": 5000}
        if config.MONGODB_URI.startswith("mongodb+srv"):
            opciones["tlsCAFile"] = certifi.where()
        _cliente = MongoClient(config.MONGODB_URI, **opciones)

    bd = _cliente[config.DB_NAME]

    if not _indices_listos:
        # Los índices hacen rápidas las consultas "aprobadas, las más recientes primero"
        bd.noticias.create_index([("estado", 1), ("fecha_publicacion", -1)])
        bd.noticias.create_index([("estado", 1), ("fecha_creacion", -1)])
        bd.opiniones.create_index([("estado", 1), ("fecha_publicacion", -1)])
        bd.opiniones.create_index([("estado", 1), ("fecha_creacion", -1)])
        bd.videos.create_index([("estado", 1), ("fecha_publicacion", -1)])
        bd.videos.create_index([("estado", 1), ("fecha_creacion", -1)])
        _indices_listos = True

    return bd
