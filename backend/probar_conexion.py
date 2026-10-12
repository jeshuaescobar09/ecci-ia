"""Comprueba la conexión con MongoDB Atlas y explica los errores más comunes.

Uso:  python probar_conexion.py
"""
import sys

import config


def main():
    print("Probando la conexión con MongoDB Atlas...\n")

    if not config.MONGODB_URI:
        print("FALTA MONGODB_URI.")
        print("  1. Copia el archivo  backend/.env.example  como  backend/.env")
        print("  2. Pega tu cadena de conexión de Atlas en MONGODB_URI")
        return 1

    from db import get_db

    try:
        bd = get_db()
        bd.command("ping")
    except Exception as error:
        nombre = type(error).__name__
        texto = str(error)
        print("NO SE PUDO CONECTAR (%s)\n" % nombre)
        if "Authentication failed" in texto or "bad auth" in texto:
            print("Causa probable: usuario o contraseña incorrectos.")
            print("  - Revisa el usuario y la contraseña de 'Database Access' en Atlas.")
            print("  - Si la contraseña tiene símbolos (@ : / ? # %), cámbiala por una solo con letras y números,")
            print("    o codifícala (por ejemplo @ se escribe %40).")
        elif nombre == "ServerSelectionTimeoutError" or "timed out" in texto:
            print("Causa probable: Atlas no deja entrar a tu conexión o no hay internet.")
            print("  - En Atlas abre 'Network Access' y agrega tu IP actual (o 0.0.0.0/0 solo para pruebas).")
            print("  - Algunas redes de universidades bloquean el puerto 27017: prueba con un hotspot del celular.")
        elif "DNS" in texto or "resolution" in texto.lower():
            print("Causa probable: la dirección del clúster está mal escrita o falla el DNS.")
            print("  - Copia de nuevo la cadena de conexión desde Atlas (Connect > Drivers).")
        else:
            print("Detalle técnico:", texto[:300])
        return 1

    print("CONEXIÓN CORRECTA con la base «%s»." % config.DB_NAME)
    print("  Noticias:  %d" % bd.noticias.count_documents({}))
    print("  Opiniones: %d" % bd.opiniones.count_documents({}))
    if not config.clave_admin_valida():
        print("\nAVISO: falta ADMIN_KEY en .env (mínimo 12 caracteres); sin ella el panel /admin está desactivado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
