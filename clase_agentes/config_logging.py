"""Configuración de logging con la biblioteca estándar.

Equivalencias con log4j:
  Logger    -> logging.getLogger(nombre)
  Appender  -> Handler (StreamHandler, FileHandler)
  Layout    -> Formatter
  Level     -> logging.DEBUG / INFO / WARNING / ERROR
"""

import logging
from pathlib import Path

# Defino el formato de los mensajes de log.
# Uso mayúsculas para las variables globales que no cambian. (Es una convención para compensar que Python no tiene constante como Java)
FORMATO = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"


def configurar_logging(archivo: Path) -> None:
    """Consola en nivel INFO y archivo en nivel DEBUG."""

    # Formatter: aplica la plantilla FORMATO a cada mensaje antes de escribirlo.
    # Cambiar FORMATO cambia el aspecto de todos los mensajes, en consola y en archivo.
    formatter = logging.Formatter(FORMATO)

    # StreamHandler: muestra los mensajes en la consola.
    consola = logging.StreamHandler()
    consola.setLevel(logging.INFO)
    consola.setFormatter(formatter)

    # FileHandler: escribe los mensajes en un archivo.
    # mode="w" borra el contenido anterior en cada ejecución; mode="a" lo conserva.
    en_archivo = logging.FileHandler(archivo, mode="w", encoding="utf-8")
    en_archivo.setLevel(logging.DEBUG)
    en_archivo.setFormatter(formatter)

    # Logger raíz (equivale al rootLogger de log4j).
    #
    # 1. Qué es: los loggers forman un árbol según su nombre, separado por puntos.
    #    "clase_agentes.agente" es hijo de "clase_agentes", y este es hijo del
    #    logger raíz. Los loggers de las bibliotecas (httpx, openai, pydantic_ai)
    #    también cuelgan de la raíz.
    #    logging.getLogger() sin argumentos devuelve el logger raíz.
    #
    # 2. Cómo viaja un mensaje: cuando un logger recibe un mensaje, lo entrega a
    #    sus propios handlers y luego lo pasa a su logger padre, hasta llegar a
    #    la raíz. Este comportamiento se llama propagación (propagate=True por
    #    defecto). Por eso basta con agregar los handlers a la raíz: reciben los
    #    mensajes de todos los módulos del programa y de todas las bibliotecas.
    #
    # 3. Por qué setLevel(DEBUG): el nivel de la raíz es WARNING por defecto.
    #    Un mensaje INFO o DEBUG se descartaría antes de llegar a los handlers.
    #    Con DEBUG en la raíz, el mensaje pasa, y cada handler decide después
    #    según su propio nivel: consola muestra desde INFO, archivo desde DEBUG.
    #
    #    Jerarquía de niveles, de menor a mayor severidad (valor numérico):
    #      DEBUG    (10)  detalle para diagnóstico: mensajes y fichas leídas.
    #      INFO     (20)  hechos normales: pregunta, llamada a herramienta, respuesta.
    #      WARNING  (30)  algo inesperado que no detiene el programa: ficha no encontrada.
    #      ERROR    (40)  una operación falló.
    #      CRITICAL (50)  el programa no puede continuar.
    #    Un logger o handler con nivel N deja pasar los mensajes de nivel N o
    #    superior. Con nivel INFO (20) pasan INFO, WARNING, ERROR y CRITICAL;
    #    DEBUG se descarta.
    #
    # 4. Por qué handlers.clear(): si configurar_logging() se ejecuta dos veces,
    #    sin esta línea cada mensaje se escribiría duplicado.
    raiz = logging.getLogger()
    raiz.setLevel(logging.DEBUG)
    raiz.handlers.clear()
    raiz.addHandler(consola)
    raiz.addHandler(en_archivo)

    # Las bibliotecas de red generan mucho DEBUG que no aporta a la clase.
    for ruidosa in ("httpx", "httpcore", "openai"):
        # Limito el nivel de log de estas bibliotecas a WARNING para no saturar la consola
        # y que no se mezclen los mensajes de log con los nuestros.
        logging.getLogger(ruidosa).setLevel(logging.WARNING)
