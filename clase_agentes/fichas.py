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
    """Minúsculas, sin tildes, con guiones bajos convertidos en espacios."""
    sin_tildes = unicodedata.normalize("NFKD", texto)
    sin_tildes = "".join(c for c in sin_tildes if not unicodedata.combining(c))
    return " ".join(sin_tildes.lower().replace("_", " ").split())


def _indice(directorio: Path) -> dict[str, Path]:
    """Mapea el nombre normalizado de cada archivo .md a su ruta."""
    return {normalizar(f.stem): f for f in directorio.glob("*.md")}


def listar_fichas(directorio: Path) -> list[str]:
    """Devuelve el nombre de cada alumno, tomado del título de su ficha."""
    nombres = []
    for ficha in sorted(_indice(directorio).values()):
        titulo = ficha.read_text(encoding="utf-8").splitlines()[0]
        nombres.append(titulo.removeprefix("# ").strip())
    return nombres


def buscar_ficha(directorio: Path, nombre: str) -> str | None:
    """Devuelve el contenido de la ficha, o None si no existe."""
    ficha = _indice(directorio).get(normalizar(nombre))
    if ficha is None:
        logger.warning("Ficha no encontrada para el nombre %r", nombre)
        return None
    logger.debug("Ficha encontrada: %s", ficha.name)
    return ficha.read_text(encoding="utf-8")
