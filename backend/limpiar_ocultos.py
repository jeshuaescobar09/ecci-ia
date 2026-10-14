"""Borra de Atlas todo lo que NO se ve en la página (estado pendiente o rechazada).

Uso (dentro de backend, con el .venv activado):
    python limpiar_ocultos.py          -> solo muestra qué se borraría
    python limpiar_ocultos.py --borrar -> guarda respaldo_ocultos.json y borra
"""
import sys

from bson import json_util

from db import get_db
from imagenes import borrar_imagen

COLECCIONES = ("noticias", "opiniones", "comentarios", "videos")
OCULTO = {"estado": {"$ne": "aprobada"}}


def main():
    bd = get_db()
    ocultos = {c: list(bd[c].find(OCULTO)) for c in COLECCIONES}

    for col, docs in ocultos.items():
        for d in docs:
            print(col, "|", d.get("estado"), "|", d.get("titulo") or d.get("nombre"))
    if not any(ocultos.values()):
        print("No hay nada oculto. La base está limpia.")
        return
    if "--borrar" not in sys.argv:
        print("\nNo se borró nada. Para borrar escribe: python limpiar_ocultos.py --borrar")
        return

    with open("respaldo_ocultos.json", "w", encoding="utf-8") as f:
        f.write(json_util.dumps(ocultos, indent=1, ensure_ascii=False))
    print("\nRespaldo guardado en respaldo_ocultos.json")

    for n in ocultos["noticias"]:
        if n.get("imagen_url"):
            borrar_imagen(n["imagen_url"])

    # Comentarios y «me gusta» que colgaban de opiniones que se van a borrar
    ids = [o["_id"] for o in ocultos["opiniones"]]
    bd.comentarios.delete_many({"opinion_id": {"$in": ids}})
    bd.me_gusta.delete_many({"opinion_id": {"$in": ids}})

    for col in COLECCIONES:
        print(col, "borrados:", bd[col].delete_many(OCULTO).deleted_count)


if __name__ == "__main__":
    main()
