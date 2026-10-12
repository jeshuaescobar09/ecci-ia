"""Arranca el portal con una base de datos FALSA en memoria.

Sirve para ver el portal y probar el panel de moderación SIN MongoDB Atlas.
Los datos se pierden al cerrar el servidor.

Uso (desde la carpeta backend):
    python tests/servidor_demo.py
Luego abre http://localhost:8000   (moderación: http://localhost:8000/admin, clave: clave-de-demostracion)
"""
import os
import sys
import tempfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "tests"))

os.environ["MONGODB_URI"] = "mongodb://demo"
os.environ.setdefault("ADMIN_KEY", "clave-de-demostracion")
os.environ.setdefault("UPLOADS_DIR", tempfile.mkdtemp(prefix="ecci_demo_uploads_"))

import fakemongo  # noqa: E402

fakemongo.instalar()

import main  # noqa: E402
import seed  # noqa: E402

seed.sembrar(main.get_db())
puerto = int(os.environ.get("PUERTO", "8000"))
print("MODO DEMOSTRACIÓN: datos en memoria. Portal: http://localhost:%d  Moderación: /admin" % puerto)
main.app.run(host="127.0.0.1", port=puerto, debug=False)
