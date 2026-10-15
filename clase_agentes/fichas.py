"""Acceso a las fichas de alumnos (archivos .md de un directorio).

La búsqueda compara el nombre pedido contra los archivos que existen.
El texto recibido nunca forma parte de una ruta, así que un valor como
"../../.env" no puede leer archivos fuera del directorio de fichas.
"""

import logging
import unicodedata
from pathlib import Path

logger = logging.getLogger(__name__)


def normalizar(texto: str) -> str:
    """Convierte un nombre a una forma comparable.

    Args:
        texto (str): Nombre o nombre de archivo, por ejemplo "Juan Pérez"
            o "juan_perez".

    Returns:
        str: Texto en minúsculas, sin tildes, con los guiones bajos
        convertidos en espacios y sin espacios repetidos. Ejemplo:
        "juan perez".
    """
    sin_tildes = unicodedata.normalize("NFKD", texto)
    sin_tildes = "".join(c for c in sin_tildes if not unicodedata.combining(c))
    return " ".join(sin_tildes.lower().replace("_", " ").split())


def _indice(directorio: Path) -> dict[str, Path]:
    """Indexa las fichas del directorio por nombre normalizado.

    Args:
        directorio (Path): Directorio que contiene los archivos .md.

    Returns:
        dict[str, Path]: Diccionario con el nombre normalizado de cada
        archivo como clave y su ruta como valor. Ejemplo:
        {"juan perez": Path("fichas/juan_perez.md")}.
    """
    return {normalizar(f.stem): f for f in directorio.glob("*.md")}


def listar_fichas(directorio: Path) -> list[str]:
    """Lista los alumnos que tienen ficha.

    Args:
        directorio (Path): Directorio que contiene los archivos .md.

    Returns:
        list[str]: Nombre de cada alumno, tomado de la primera línea de su
        ficha sin el prefijo "# ". Ejemplo: ["Juan Pérez", "María Gómez"].
    """
    nombres = []
    for ficha in sorted(_indice(directorio).values()):
        titulo = ficha.read_text(encoding="utf-8").splitlines()[0]
        nombres.append(titulo.removeprefix("# ").strip())
    return nombres


def buscar_ficha(directorio: Path, nombre: str) -> str | None:
    """Busca la ficha de un alumno por nombre.

    El texto de `nombre` se usa como clave de búsqueda y nunca forma parte
    de una ruta (prevención de path traversal).

    Args:
        directorio (Path): Directorio que contiene los archivos .md.
        nombre (str): Nombre del alumno. Se ignoran las mayúsculas y las
            tildes.

    Returns:
        str | None: Contenido de la ficha, o None si no existe una ficha
        para ese nombre.
    """
    ficha = _indice(directorio).get(normalizar(nombre))
    if ficha is None:
        logger.warning("Ficha no encontrada para el nombre %r", nombre)
        return None
    logger.debug("Ficha encontrada: %s", ficha.name)
    return ficha.read_text(encoding="utf-8")
