"""Registro en el log de los turnos que resuelve pydantic-ai.

Un turno es una request al modelo (ModelRequest) y la respuesta del modelo
(ModelResponse). pydantic-ai encadena turnos automáticamente: si el modelo
pide una herramienta, pydantic-ai la ejecuta, envía el resultado en una nueva
request y repite hasta que el modelo entrega la respuesta final.

pydantic-ai no escribe estos eventos con el módulo logging, así que este
módulo los reconstruye a partir de result.all_messages().
"""

import logging
from collections.abc import Sequence

from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    RetryPromptPart,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)

logger = logging.getLogger(__name__)

LARGO_MAXIMO = 120


def _resumir(valor: object) -> str:
    """Convierte un valor en una sola línea de largo acotado.

    Args:
        valor (object): Contenido de un mensaje: pregunta, resultado de una
            herramienta o texto del modelo.

    Returns:
        str: Texto con los saltos de línea reemplazados por espacios y
        cortado en LARGO_MAXIMO caracteres, con "..." si se cortó.
    """
    texto = " ".join(str(valor).split())
    if len(texto) > LARGO_MAXIMO:
        return texto[:LARGO_MAXIMO] + "..."
    return texto


def _registrar_request(turno: int, mensaje: ModelRequest) -> None:
    """Registra lo que pydantic-ai envía al modelo en un turno.

    Args:
        turno (int): Número del turno, desde 1.
        mensaje (ModelRequest): Request con las partes enviadas al modelo.

    Returns:
        None: Escribe una línea INFO por cada parte.
    """
    for parte in mensaje.parts:
        if isinstance(parte, UserPromptPart):
            logger.info("Turno %d | pydantic-ai envía al modelo la pregunta: %s",
                        turno, _resumir(parte.content))
        elif isinstance(parte, ToolReturnPart):
            logger.info("Turno %d | pydantic-ai envía al modelo el resultado de %s: %s",
                        turno, parte.tool_name, _resumir(parte.content))
        elif isinstance(parte, RetryPromptPart):
            logger.info("Turno %d | pydantic-ai pide al modelo que corrija: %s",
                        turno, _resumir(parte.content))


def _registrar_response(turno: int, mensaje: ModelResponse) -> None:
    """Registra lo que el modelo responde en un turno.

    Args:
        turno (int): Número del turno, desde 1.
        mensaje (ModelResponse): Respuesta del modelo con sus partes y su
            uso de tokens.

    Returns:
        None: Escribe una línea INFO por cada parte y una con los tokens.
    """
    for parte in mensaje.parts:
        if isinstance(parte, ToolCallPart):
            logger.info("Turno %d | el modelo pide ejecutar %s(%s)",
                        turno, parte.tool_name, _resumir(parte.args_as_dict()))
        elif isinstance(parte, TextPart):
            logger.info("Turno %d | el modelo entrega texto: %s",
                        turno, _resumir(parte.content))
    logger.info("Turno %d | tokens: entrada=%d, salida=%d",
                turno, mensaje.usage.input_tokens, mensaje.usage.output_tokens)


def registrar_turnos(mensajes: Sequence[ModelMessage]) -> None:
    """Escribe en el log, en nivel INFO, cada turno de una ejecución.

    Args:
        mensajes (Sequence[ModelMessage]): Mensajes intercambiados, tal como
            los devuelve result.all_messages().

    Returns:
        None: Escribe líneas INFO con el formato "Turno N | ...".
    """
    turno = 0
    for mensaje in mensajes:
        if isinstance(mensaje, ModelRequest):
            turno += 1
            _registrar_request(turno, mensaje)
        elif isinstance(mensaje, ModelResponse):
            _registrar_response(turno, mensaje)
