"""Carga noticias y opiniones de EJEMPLO para que el portal no se vea vacío.

Uso:
    python seed.py             # solo carga datos si la base está vacía
    python seed.py --forzar    # reemplaza los ejemplos anteriores (no toca lo que escribió la gente)

Todo lo que carga este script lleva la marca  semilla: True  y estado "aprobada".
Cuando tengas noticias reales, bórralas desde el panel de moderación.
"""
import sys
from datetime import datetime, timedelta, timezone

AUTOR = "Redacción ECCI"
CORREO = "redaccion@ejemplo.cr"

# (horas atrás, categoría, título, resumen, párrafos, imagen)
NOTICIAS = [
    (
        1,
        "Inteligencia artificial",
        "¡La IA llegó a la ECCI! Un robot, cientos de curiosos y el futuro de la computación en la UCR",
        "La ECCI abrió sus puertas a la inteligencia artificial y la comunidad estudiantil respondió: "
        "pasillos llenos, celulares en alto y una pregunta en el aire, ¿cómo será trabajar junto a las máquinas?",
        [
            "La Escuela de Ciencias de la Computación e Informática abrió sus puertas a la inteligencia artificial "
            "con una actividad en la que estudiantes y docentes se acercaron a conocer de cerca un robot humanoide "
            "y las tecnologías que lo hacen posible.",
            "La iniciativa busca acercar la IA a toda la comunidad universitaria y fomentar el debate sobre su uso "
            "responsable. (Texto de ejemplo: reemplázalo por la noticia real desde el panel de moderación.)",
        ],
        "imagenes/robot-ia.jpg",
    ),
    (
        3,
        "Big Data",
        "Laboratorio de datos abre cupos para proyectos de Big Data",
        "Estudiantes interesados en análisis de grandes volúmenes de datos podrán sumarse a proyectos "
        "del laboratorio durante el próximo ciclo.",
        [
            "El laboratorio recibirá propuestas de estudiantes que quieran practicar con datos reales, desde la "
            "limpieza hasta la visualización de resultados.",
            "Texto de ejemplo para mostrar cómo se ve una noticia publicada en el portal.",
        ],
        None,
    ),
    (
        6,
        "Proyectos estudiantiles",
        "Asistente de voz permite controlar la PC sin teclado ni mouse",
        "Un proyecto estudiantil usa reconocimiento de voz para que personas con discapacidad motora "
        "puedan manejar el computador con comandos hablados.",
        [
            "El asistente interpreta órdenes como abrir programas o escribir texto, y está pensado para ser "
            "fácil de instalar y de usar.",
            "Texto de ejemplo para mostrar cómo se ve una noticia publicada en el portal.",
        ],
        None,
    ),
    (
        26,
        "Procesamiento de lenguaje natural",
        "Así aprenden las máquinas a entender el español de Costa Rica",
        "El procesamiento de lenguaje natural enfrenta un reto particular: los modismos y expresiones "
        "propias de cada país.",
        [
            "Los modelos de lenguaje se entrenan con grandes cantidades de texto, y el español de cada región "
            "tiene giros que no siempre están bien representados.",
            "Texto de ejemplo para mostrar cómo se ve una noticia publicada en el portal.",
        ],
        None,
    ),
    (
        30,
        "Eventos",
        "Feria científica: los proyectos de IA que podrás ver en vivo",
        "La feria reunirá demostraciones de inteligencia artificial, datos y accesibilidad creadas por estudiantes.",
        [
            "Habrá estaciones para probar los proyectos y conversar con quienes los desarrollaron.",
            "Texto de ejemplo para mostrar cómo se ve una noticia publicada en el portal.",
        ],
        None,
    ),
    (
        50,
        "Bases de datos",
        "Del Excel a la nube: cómo ordenar la información de una institución",
        "Pasar de hojas de cálculo sueltas a una base de datos en la nube mejora el control y la seguridad "
        "de la información.",
        [
            "Una base de datos bien diseñada evita duplicados, permite buscar rápido y deja registro de los cambios.",
            "Texto de ejemplo para mostrar cómo se ve una noticia publicada en el portal.",
        ],
        None,
    ),
    (
        74,
        "Inteligencia artificial",
        "Montan un servidor de modelos de lenguaje propio en la escuela",
        "Un equipo instaló modelos de lenguaje en un computador de la escuela para practicar sin depender "
        "de servicios externos.",
        [
            "Correr los modelos de forma local permite experimentar con privacidad y sin costos por uso.",
            "Texto de ejemplo para mostrar cómo se ve una noticia publicada en el portal.",
        ],
        None,
    ),
    (
        98,
        "Proyectos estudiantiles",
        "Convocatoria abierta para escribir en el portal ECCI.IA",
        "Cualquier estudiante puede enviar su noticia; un moderador la revisa antes de publicarla.",
        [
            "Usa el botón «Subir noticia», completa el formulario y espera la aprobación.",
            "Texto de ejemplo para mostrar cómo se ve una noticia publicada en el portal.",
        ],
        None,
    ),
    (
        120,
        "Big Data",
        "Datos que hablan: la ECCI enseña a convertir millones de registros en decisiones",
        "Estudiantes de Bases de Datos y Análisis de Datos muestran cómo la visualización transforma "
        "cifras en historias claras.",
        [
            "La visualización de datos ayuda a detectar patrones que una tabla de números esconde.",
            "Texto de ejemplo para mostrar cómo se ve una noticia publicada en el portal.",
        ],
        None,
    ),
    (
        144,
        "Procesamiento de lenguaje natural",
        "¿Pueden las máquinas entendernos? Los chatbots universitarios dan sus primeros pasos",
        "El Procesamiento de Lenguaje Natural llega a las aulas con prácticas reales y modelos que "
        "corren en equipos locales.",
        [
            "Los estudiantes aprenden a preparar textos, entrenar modelos y evaluar sus respuestas.",
            "Texto de ejemplo para mostrar cómo se ve una noticia publicada en el portal.",
        ],
        None,
    ),
    (
        168,
        "Proyectos estudiantiles",
        "Tecnología sin barreras: proyectos de voz abren la computadora a más personas",
        "Una nueva generación de aplicaciones busca que el control de un computador sea posible "
        "para personas con discapacidad motora.",
        [
            "La accesibilidad se vuelve un criterio de diseño desde el inicio de cada proyecto.",
            "Texto de ejemplo para mostrar cómo se ve una noticia publicada en el portal.",
        ],
        None,
    ),
]

# (horas atrás, nombre, tema, texto)
OPINIONES = [
    (1, "María", "La IA en las aulas",
     "Creo que la IA debe usarse como herramienta de apoyo, nunca para reemplazar el aprendizaje. "
     "Lo importante es entender qué hace por dentro."),
    (3, "Diego", "Futuro laboral",
     "Los perfiles que sepan trabajar con datos y modelos van a tener mucha ventaja. "
     "La ECCI nos está preparando para eso."),
    (26, "Andrea", "Ética y uso responsable",
     "Falta hablar más de privacidad y sesgos. Una IA es tan justa como los datos con los que aprende."),
]


def sembrar(bd, forzar=False):
    """Inserta los ejemplos. Devuelve (noticias, opiniones) o None si no hizo nada."""
    if forzar:
        bd.noticias.delete_many({"semilla": True})
        bd.opiniones.delete_many({"semilla": True})
    elif bd.noticias.count_documents({}) > 0 or bd.opiniones.count_documents({}) > 0:
        return None

    ahora = datetime.now(timezone.utc)

    noticias = []
    for horas, categoria, titulo, resumen, parrafos, imagen in NOTICIAS:
        fecha = ahora - timedelta(hours=horas)
        noticias.append(
            {
                "titulo": titulo,
                "resumen": resumen,
                "contenido": "\n\n".join(parrafos),
                "categoria": categoria,
                "autor": AUTOR,
                "correo": CORREO,
                "imagen_url": imagen,
                "estado": "aprobada",
                "motivo_rechazo": None,
                "fecha_creacion": fecha,
                "fecha_publicacion": fecha,
                "semilla": True,
            }
        )

    opiniones = []
    for horas, nombre, tema, texto in OPINIONES:
        fecha = ahora - timedelta(hours=horas)
        opiniones.append(
            {
                "nombre": nombre,
                "tema": tema,
                "texto": texto,
                "estado": "aprobada",
                "motivo_rechazo": None,
                "fecha_creacion": fecha,
                "fecha_publicacion": fecha,
                "semilla": True,
            }
        )

    bd.noticias.insert_many(noticias)
    bd.opiniones.insert_many(opiniones)
    return len(noticias), len(opiniones)


if __name__ == "__main__":
    from db import get_db

    resultado = sembrar(get_db(), forzar="--forzar" in sys.argv)
    if resultado is None:
        print("La base ya tiene datos: no se agregó nada. Usa  python seed.py --forzar  para reemplazar los ejemplos.")
    else:
        print("Listo: %d noticias y %d opiniones de ejemplo cargadas." % resultado)
