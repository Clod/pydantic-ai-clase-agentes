"""Agente pydantic-ai que responde preguntas sobre fichas de alumnos.

Flujo: pregunta -> modelo -> llamada a herramienta -> ficha -> modelo
-> respuesta validada como RespuestaAlumno.

Ejecución:  python agente.py  (lee OPENROUTER_API_KEY desde .env)
"""

import logging
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic_ai import Agent, ModelRetry, RunContext
from pydantic_ai.models.openrouter import OpenRouterModel
from pydantic_ai.providers.openrouter import OpenRouterProvider

from config_logging import configurar_logging
from fichas import buscar_ficha, listar_fichas

logger = logging.getLogger("clase_agentes.agente")

AQUI = Path(__file__).parent
load_dotenv(AQUI / ".env")  # antes de leer MODELO; no pisa variables ya definidas
PREGUNTA = "¿Qué promedio tiene Juan Pérez?"
MODELO = os.environ.get("OPENROUTER_MODEL", "anthropic/claude-haiku-5.5")


# 1. Salida tipada: pydantic-ai valida la respuesta del modelo contra esta clase.
class RespuestaAlumno(BaseModel):
    nombre: str
    carrera: str
    promedio: float = Field(ge=0, le=10)


# 2. Dependencias: datos que las herramientas necesitan y el modelo no controla.
@dataclass(frozen=True)
class Deps:
    directorio: Path


# 3. Agente: el modelo se indica al ejecutar, no al crear el agente.
agent = Agent(
    deps_type=Deps,
    output_type=RespuestaAlumno,
    retries=2,
    instructions=(
        "Respondé preguntas sobre alumnos. Usá las herramientas para obtener "
        "los datos. No inventes datos que no estén en una ficha."
    ),
)


# 4. Herramientas. El parámetro `ctx` no aparece en el esquema que ve el modelo.
@agent.tool
def listar_alumnos(ctx: RunContext[Deps]) -> list[str]:
    """Devuelve los nombres de todos los alumnos disponibles."""
    nombres = listar_fichas(ctx.deps.directorio)
    logger.info("Herramienta listar_alumnos -> %d alumnos", len(nombres))
    return nombres


@agent.tool
def buscar_alumno(ctx: RunContext[Deps], nombre: str) -> str:
    """Devuelve la ficha (nombre, edad, carrera, promedio) de un alumno."""
    logger.info("Herramienta buscar_alumno(nombre=%r)", nombre)
    ficha = buscar_ficha(ctx.deps.directorio, nombre)
    if ficha is None:
        # ModelRetry devuelve este mensaje al modelo para que corrija el argumento.
        raise ModelRetry(
            f"No existe una ficha para {nombre!r}. "
            "Llamá a listar_alumnos para ver los nombres disponibles."
        )
    return ficha


def crear_modelo() -> OpenRouterModel:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise SystemExit("Falta la variable de entorno OPENROUTER_API_KEY.")
    return OpenRouterModel(MODELO, provider=OpenRouterProvider(api_key=api_key))


def main() -> None:
    configurar_logging(AQUI / "clase_agentes.log")
    logger.info("Pregunta: %s", PREGUNTA)
    logger.info("Modelo: %s", MODELO)

    result = agent.run_sync(
        PREGUNTA,
        model=crear_modelo(),
        deps=Deps(directorio=AQUI / "fichas"),
    )

    for mensaje in result.all_messages():
        logger.debug("Mensaje: %r", mensaje)
    logger.info("Uso: %s", result.usage())
    logger.info("Respuesta: %s", result.output)


if __name__ == "__main__":
    main()
