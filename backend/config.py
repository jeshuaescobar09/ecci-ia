"""Configuración del servidor.

Los valores se leen de backend/.env (copia .env.example y rellénalo).
Aquí también están las listas de categorías y temas permitidos.
"""
import os
from pathlib import Path
from urllib.parse import unquote, urlsplit

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR.parent  # carpeta con index.html, styles.css, app.js, imagenes/

# Las variables que ya existan en el sistema tienen prioridad sobre el archivo .env
load_dotenv(BASE_DIR / ".env")


def _lista(valor):
    return [x.strip() for x in valor.split(",") if x.strip()]


# --- Base de datos (MongoDB Atlas) ---
MONGODB_URI = os.getenv("MONGODB_URI", "").strip()
DB_NAME = os.getenv("DB_NAME", "ecci_ia").strip()

# --- Moderación ---
ADMIN_KEY = os.getenv("ADMIN_KEY", "").strip()
CLAVE_EJEMPLO = "cambia-esta-clave-por-una-larga"

# Si pones dominios (ucr.ac.cr), solo se aceptan correos de esos dominios.
DOMINIOS_PERMITIDOS = [d.lower().lstrip("@") for d in _lista(os.getenv("DOMINIOS_PERMITIDOS", ""))]

# Páginas que pueden llamar a la API desde otro origen (Live Server, archivo local, etc.)
CORS_ORIGINS = _lista(
    os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5500,http://127.0.0.1:5500,http://localhost:8000,http://127.0.0.1:8000,null",
    )
)

# --- Límites contra abuso ---
LIMITE_ENVIOS = int(os.getenv("LIMITE_ENVIOS", "5"))  # envíos por persona...
VENTANA_ENVIOS = int(os.getenv("VENTANA_ENVIOS_SEGUNDOS", "600"))  # ...cada 10 minutos
MAX_IMAGEN_MB = 5

# --- Archivos subidos ---
UPLOADS_DIR = Path(os.getenv("UPLOADS_DIR", str(BASE_DIR / "uploads")))

# --- Imágenes en la nube (Cloudinary) ---
# Formato: cloudinary://API_KEY:API_SECRET@CLOUD_NAME  (se copia del panel de Cloudinary)
# Si está vacía, las imágenes se guardan en UPLOADS_DIR como siempre.
_nube = urlsplit(os.getenv("CLOUDINARY_URL", "").strip())
CLOUDINARY_CLOUD = (_nube.hostname or "") if _nube.scheme == "cloudinary" else ""
CLOUDINARY_KEY = unquote(_nube.username or "") if CLOUDINARY_CLOUD else ""
CLOUDINARY_SECRET = unquote(_nube.password or "") if CLOUDINARY_CLOUD else ""


def usa_cloudinary():
    return bool(CLOUDINARY_CLOUD and CLOUDINARY_KEY and CLOUDINARY_SECRET)


# --- Servidor ---
HOST = os.getenv("HOST", "127.0.0.1")
PUERTO = int(os.getenv("PUERTO") or os.getenv("PORT") or "8000")  # Render define PORT solo
DEBUG = os.getenv("DEBUG", "1") == "1"
# Solo en el hosting (Render): confiar en la IP que manda su proxy. En tu PC déjalo apagado.
DETRAS_DE_PROXY = os.getenv("DETRAS_DE_PROXY", "0") == "1"

# --- Listas permitidas (deben coincidir con los <select> de index.html) ---
CATEGORIAS = [
    "Inteligencia artificial",
    "Big Data",
    "Bases de datos",
    "Procesamiento de lenguaje natural",
    "Eventos",
    "Proyectos estudiantiles",
]

CATEGORIAS_VIDEO = [
    "Charla",
    "Demostración",
    "Proyecto estudiantil",
    "Evento",
    "Tutorial",
]

TEMAS_OPINION = [
    "La IA en las aulas",
    "Ética y uso responsable",
    "Futuro laboral",
    "Otro tema",
]


def clave_admin_valida():
    """La clave de administrador debe existir, ser larga y no ser la de ejemplo."""
    return len(ADMIN_KEY) >= 12 and ADMIN_KEY != CLAVE_EJEMPLO
