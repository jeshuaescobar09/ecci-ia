"""Carga noticias REALES de la ECCI y el CITIC (resumidas) y videos de YouTube sobre IA.

Uso:
    python cargar_ecci.py            # agrega lo que todavía no esté (no duplica)
    python cargar_ecci.py --borrar   # quita todo lo que cargó este script

Los textos son resúmenes propios; cada noticia termina con el enlace a la fuente
original. Las fotos son de Wikimedia Commons con licencia libre (CC0 / CC BY / CC BY-SA):
se guardan en imagenes/noticias/ y cada noticia indica su autor y licencia.
Todo lo cargado lleva la marca  importado: True  y estado "aprobada".

    python cargar_ecci.py --sin-ejemplos   # además borra las noticias de ejemplo (seed.py) sin foto
"""
import sys
from datetime import datetime, timedelta, timezone

AUTOR = "ECCI.IA (resumen)"
CORREO = "redaccion@ejemplo.cr"

# (fecha de la fuente, categoría, título, resumen, párrafos, enlace a la fuente, foto)
NOTICIAS = [
    (
        "2026-09-28", "Eventos",
        "OIJ y la Oficina de Asuntos Internacionales visitan el CITIC",
        "Representantes del OIJ y de la OAICE recorrieron el centro de investigación para conocer su trabajo "
        "y buscar proyectos conjuntos.",
        [
            "El Centro de Investigación en Tecnologías de la Información y Comunicación (CITIC) de la UCR recibió "
            "a representantes del Organismo de Investigación Judicial (OIJ) y de la Oficina de Asuntos "
            "Internacionales y Cooperación Externa (OAICE).",
            "El objetivo de la visita fue conocer las líneas de investigación del centro y explorar posibles "
            "proyectos en conjunto.",
        ],
        "https://citic.ucr.ac.cr/noticias/visita-representantes-oaice-y-oij", "oij-visita",
    ),
    (
        "2026-09-25", "Inteligencia artificial",
        "Investigadores del CITIC estudian IA e Internet de las Cosas en China",
        "Cuatro personas investigadoras participaron en la escuela de verano de la UESTC en Chengdu, "
        "con programas de AIoT y de IA inspirada en el cerebro.",
        [
            "Del 4 al 18 de julio de 2026, cuatro personas investigadoras del CITIC asistieron a la International "
            "Summer School de la Universidad de Ciencia y Tecnología Electrónica de China (UESTC), en Chengdu.",
            "Maeva Murcia, Hansell Solís y Enrique Vílchez cursaron el programa «Future AIoT», que une la "
            "inteligencia artificial con el Internet de las Cosas. María Isabel Murillo participó en "
            "«Cognitive Science / Brain-based AI».",
            "La UESTC otorgó las becas y la OAICE financió parcialmente el viaje.",
        ],
        "https://citic.ucr.ac.cr/noticias/participacion-summer-school-uestc", "uestc",
    ),
    (
        "2026-06-24", "Eventos",
        "El CITIC celebra 15 años de investigación en computación",
        "El centro de investigación celebró su decimoquinto aniversario con un acto en el auditorio de la ECCI.",
        [
            "El Centro de Investigación en Tecnologías de la Información y Comunicación (CITIC) cumplió 15 años "
            "y lo celebró con una ceremonia en el auditorio de la Escuela de Ciencias de la Computación e "
            "Informática.",
            "Al acto asistieron varias autoridades universitarias.",
        ],
        "https://citic.ucr.ac.cr/noticias/xv-aniversario-citic", "citic-aniversario",
    ),
    (
        "2026-05-31", "Eventos",
        "JoCICI 2026: las jornadas de investigación en computación llegan a su VII edición",
        "El CITIC apoyó la organización de las Jornadas Costarricenses en Investigación en Computación e "
        "Informática, incluido su sitio web.",
        [
            "Se realizó la VII edición de las Jornadas Costarricenses en Investigación en Computación e Informática "
            "(JoCICI 2026), un espacio para presentar investigación en computación hecha en el país.",
            "El CITIC colaboró en la organización, incluyendo la construcción y el alojamiento del sitio web del evento.",
        ],
        "https://citic.ucr.ac.cr/noticias/vii-edicion-jornadas-costarricenses-investigacion-computacion-e-informatica-jocici2026", "jocici",
    ),
    (
        "2026-05-21", "Inteligencia artificial",
        "Steve Crocker, pionero de Internet, conversa con investigadores de IA de la UCR",
        "El autor del primer RFC visitó el CITIC y se reunió con el equipo que trabaja en inteligencia artificial.",
        [
            "El jueves 21 de mayo de 2026, el Dr. Steve Crocker, uno de los pioneros de Internet, recorrió las "
            "instalaciones del CITIC en la Universidad de Costa Rica.",
            "Durante la visita se reunió con personas investigadoras que trabajan en inteligencia artificial.",
            "Crocker participó en el desarrollo de los protocolos de ARPANET en UCLA, fundó el Network Working "
            "Group en 1969 y escribió el RFC 1, el primer documento de la serie que define cómo funciona Internet.",
        ],
        "https://citic.ucr.ac.cr/noticias/visita-dr-steve-crocker-al-citic", "steve-crocker",
    ),
    (
        "2026-04-20", "Inteligencia artificial",
        "Charla: IA responsable y ética para la ciberseguridad",
        "La Dra. Arati M. Dixit, de ACM-W, habló en el auditorio de la ECCI sobre el uso responsable de la IA "
        "en seguridad informática.",
        [
            "La ECCI invitó a la charla «Responsible and Ethical AI for Cybersecurity», impartida por la "
            "Dra. Arati M. Dixit el jueves 23 de abril a las 4:00 p. m. en el Auditorio ECCI (Edificio Anexo, primer piso).",
            "La Dra. Dixit preside el Comité de Actividades Regionales del equipo global de ACM-W. Investiga IA "
            "aplicada a la seguridad, ciberseguridad, sistemas ciberfísicos y tecnología educativa.",
            "Tiene un doctorado en Ingeniería en Computación de Wayne State University, ha dado más de 60 charlas "
            "y recibió en 2019 un reconocimiento de ACM por ampliar sus programas y la diversidad en India.",
        ],
        "https://www.ecci.ucr.ac.cr/noticia/charla-responsible-and-ethical-ai-cybersecurity", "ciberseguridad",
    ),
    (
        "2026-04-19", "Eventos",
        "Charla: comunidades ACM-W que apoyan a las mujeres en computación",
        "Una consultora del Center for Inclusive Computing de Northeastern University habló sobre los "
        "capítulos locales de ACM-W.",
        [
            "La ECCI anunció la charla «ACM-W Chapters – Local communities that support, celebrate and advocate».",
            "La actividad presentó cómo funcionan los capítulos locales de ACM-W, comunidades que apoyan y "
            "visibilizan a las mujeres en la computación.",
        ],
        "https://www.ecci.ucr.ac.cr/noticia/charla-acm-w-chapters-%E2%80%93-local-communities-support-celebrate-and-advocate", "acm-w",
    ),
    (
        "2026-04-13", "Proyectos estudiantiles",
        "Estudiantes de la ECCI logran el 4.º lugar de Latinoamérica en GameJam+ con «BARRO»",
        "Seis estudiantes fueron el único equipo costarricense entre los cuatro mejores de la región "
        "y avanzaron a la final.",
        [
            "Diego Joaquín Camacho Martínez, Andrés Cedeño Mora, Arturo Daniels Fernández, Esteban Higuera Muñoz, "
            "Konstantin Latysh y Brandon Palacios Delgado obtuvieron el cuarto lugar de la región LATAM en "
            "GameJam+ 25/26 con su videojuego «BARRO».",
            "Las semifinales se realizaron del 9 al 12 de enero de 2026. Fuera de Brasil, fueron el único equipo "
            "entre los cuatro primeros lugares.",
            "El equipo avanzó a la final, programada para el 14 de mayo, y planea terminar el desarrollo del juego.",
        ],
        "https://www.ecci.ucr.ac.cr/noticia/estudiantes-de-la-ecci-quedan-4to-lugar-de-la-regi%C3%B3n-latam-en-gamejam-2526", "gamejam",
    ),
]

# Fotos libres de Wikimedia Commons: (archivo, autor, licencia, página, ¿muestra el evento real?)
FOTOS = {
    "oij-visita": ("Antonio Solera", "CC BY 3.0", "https://commons.wikimedia.org/wiki/File:OIJ_CR_1.JPG", True),
    "uestc": ("MspreilsCN", "CC0", "https://commons.wikimedia.org/wiki/File:Buildings_in_UESTC_Shahe.jpg", True),
    "citic-aniversario": ("Laura Rodriguez, Universidad de Costa Rica", "CC BY 4.0",
                          "https://commons.wikimedia.org/wiki/File:Ciudad_Universitaria_Rodrigo_Facio.jpg", True),
    "jocici": ("Haakon S. Krohn", "CC BY-SA 3.0", "https://commons.wikimedia.org/wiki/File:UCR_Generales.jpg", True),
    "steve-crocker": ("Joi Ito", "CC BY 2.0", "https://commons.wikimedia.org/wiki/File:SteveCrockerJI1.jpg", True),
    "ciberseguridad": ("Rebecca Wang", "CC BY 4.0",
                       "https://commons.wikimedia.org/wiki/File:Cybersecurity_Visuals_Challenge_2019_-_Rebecca_Wang.jpg", False),
    "acm-w": ("WOCinTech Chat", "CC BY 2.0",
              "https://commons.wikimedia.org/wiki/File:Women_In_Tech_-_79_(22543241611).jpg", False),
    "gamejam": ("Jason Krüger", "CC BY-SA 4.0", "https://commons.wikimedia.org/wiki/File:Game_Jammers_3.jpg", False),
}


def credito(foto):
    autor, licencia, pagina, real = FOTOS[foto]
    tipo = "Foto" if real else "Foto ilustrativa"
    return "%s: %s, %s, vía Wikimedia Commons (%s)" % (tipo, autor, licencia, pagina)


# (días atrás, categoría, título, descripción, id de YouTube)
VIDEOS = [
    (1, "Charla", "Hacia una Estrategia Nacional de Inteligencia Artificial en Costa Rica",
     "Video del MICITT sobre la estrategia país para el desarrollo y el uso de la IA en Costa Rica.", "UuSIjSM8igg"),
    (2, "Charla", "Avanza proyecto sobre inteligencia artificial en Costa Rica",
     "Video de la Asamblea Legislativa sobre el avance de un proyecto de ley de inteligencia artificial.", "rSLVYxvq2ME"),
    (3, "Charla", "UNA Mirada: usos y retos de la inteligencia artificial en Costa Rica",
     "Programa de UNA Comunica sobre las oportunidades y los desafíos de la IA en el país.", "o1YVnSUPkSc"),
    (4, "Charla", "Inteligencia artificial en Costa Rica, conversemos con el TEC",
     "Conversatorio del Tecnológico de Costa Rica sobre el presente y el futuro de la IA.", "8n9wpAsRIMo"),
]


def cargar(bd):
    """Inserta lo que falte y pone la foto a lo ya cargado. Devuelve (noticias nuevas, videos nuevos)."""
    nuevas = 0
    for fecha_txt, categoria, titulo, resumen, parrafos, fuente, foto in NOTICIAS:
        contenido = "\n\n".join(parrafos + ["Fuente: " + fuente, credito(foto)])
        imagen = "imagenes/noticias/%s.jpg" % foto
        if bd.noticias.count_documents({"titulo": titulo}) > 0:
            bd.noticias.update_one({"titulo": titulo, "importado": True},
                                   {"$set": {"imagen_url": imagen, "contenido": contenido}})
            continue
        fecha = datetime.strptime(fecha_txt, "%Y-%m-%d").replace(hour=12, tzinfo=timezone.utc)
        bd.noticias.insert_one({
            "titulo": titulo, "resumen": resumen, "contenido": contenido, "categoria": categoria,
            "autor": AUTOR, "correo": CORREO, "imagen_url": imagen,
            "estado": "aprobada", "motivo_rechazo": None,
            "fecha_creacion": fecha, "fecha_publicacion": fecha, "importado": True,
        })
        nuevas += 1

    ahora = datetime.now(timezone.utc)
    nuevos = 0
    for dias, categoria, titulo, descripcion, youtube_id in VIDEOS:
        if bd.videos.count_documents({"youtube_id": youtube_id}) > 0:
            continue
        fecha = ahora - timedelta(days=dias)
        bd.videos.insert_one({
            "titulo": titulo, "descripcion": descripcion, "categoria": categoria, "youtube_id": youtube_id,
            "autor": AUTOR, "correo": CORREO,
            "estado": "aprobada", "motivo_rechazo": None,
            "fecha_creacion": fecha, "fecha_publicacion": fecha, "importado": True,
        })
        nuevos += 1
    return nuevas, nuevos


def quitar_ejemplos_sin_foto(bd):
    """Borra solo las noticias de ejemplo de seed.py que no tienen imagen."""
    return bd.noticias.delete_many({"semilla": True, "imagen_url": None}).deleted_count


def borrar(bd):
    return (bd.noticias.delete_many({"importado": True}).deleted_count,
            bd.videos.delete_many({"importado": True}).deleted_count)


if __name__ == "__main__":
    from db import get_db

    if "--borrar" in sys.argv:
        print("Borradas: %d noticias y %d videos importados." % borrar(get_db()))
    else:
        print("Listo: %d noticias y %d videos nuevos cargados (fotos al día)." % cargar(get_db()))
        if "--sin-ejemplos" in sys.argv:
            print("Borradas %d noticias de ejemplo sin foto." % quitar_ejemplos_sin_foto(get_db()))
