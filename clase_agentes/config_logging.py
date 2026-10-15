"""Configuración de logging con la biblioteca estándar.

Equivalencias con log4j:
  Logger    -> logging.getLogger(nombre)
  Appender  -> Handler (StreamHandler, FileHandler)
  Layout    -> Formatter
  Level     -> logging.DEBUG / INFO / WARNING / ERROR
"""

import logging
from pathlib import Path

FORMATO = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"


def configurar_logging(archivo: Path) -> None:
    """Consola en nivel INFO y archivo en nivel DEBUG."""
    formatter = logging.Formatter(FORMATO)

    consola = logging.StreamHandler()
    consola.setLevel(logging.INFO)
    consola.setFormatter(formatter)

    en_archivo = logging.FileHandler(archivo, mode="w", encoding="utf-8")
    en_archivo.setLevel(logging.DEBUG)
    en_archivo.setFormatter(formatter)

    # El logger raíz deja pasar DEBUG; cada handler filtra según su nivel.
    raiz = logging.getLogger()
    raiz.setLevel(logging.DEBUG)
    raiz.handlers.clear()
    raiz.addHandler(consola)
    raiz.addHandler(en_archivo)

    # Las bibliotecas de red generan mucho DEBUG que no aporta a la clase.
    for ruidosa in ("httpx", "httpcore", "openai"):
        logging.getLogger(ruidosa).setLevel(logging.WARNING)
