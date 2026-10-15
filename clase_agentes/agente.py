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

# Defino la etiqueta para que el logger marque los eventos de este módulo.
logger = logging.getLogger("clase_agentes.agente")


# __file__ es una variable que Python define en cada módulo. Contiene la ruta del archivo que se está ejecutando: .../clase_agentes/agente.py.
# Path(__file__) convierte ese texto en un objeto Path de pathlib.
# .parent devuelve el directorio que contiene el archivo: .../clase_agentes.
# AQUI guarda ese directorio. El nombre va en mayúsculas porque es una constante por convención.
AQUI = Path(__file__).parent
load_dotenv(AQUI / ".env")  # antes de leer MODELO; no pisa variables ya definidas
# Hardodeamos la pregunta para simplificar el ejemplo, pero podría pasarse como parámetro por línea de comandos.
PREGUNTA = "¿Qué promedio tiene Juan Pérez?"
# Tomamos el modelo de la variable de entorno OPENROUTER_MODEL. Si no existe, usamos anthropic/claude-haiku-5.5.
# La variable de entorno se define en el archivo .env, que no se sube a GitHub.
MODELO = os.environ.get("OPENROUTER_MODEL", "anthropic/claude-haiku-5.5")


# Defino una clase para estructurar la respuesta del agente. Pydantic se encarga de validar que la respuesta sea correcta.
# Esto es una gran ventaja de pydantic-ai, ya que evita errores de tipeo y asegura que la respuesta sea correcta.
class RespuestaAlumno(BaseModel):
    nombre: str
    carrera: str
    promedio: float = Field(ge=0, le=10)


# Defino las dependencias: datos que las herramientas necesitan y el modelo no controla.
# En este caso, el directorio donde se encuentran las fichas.
@dataclass(frozen=True) # frozen=True significa que el objeto no se puede modificar después de crearlo.
class Deps:
    directorio: Path


# Defino el agente: el modelo se indica al ejecutar, NO al crear el agente.
agent = Agent(
    # deps_type indica que el agente necesita dependencias y cuál es su tipo.
    deps_type=Deps,
    # output_type indica el tipo de salida esperada.
    output_type=RespuestaAlumno,
    # retries indica cuántas veces se reintenta la llamada al modelo en caso de error al procesar la respuesta.
    retries=2,
    # instructions indica las instrucciones que se le dan al agente.
    instructions=(
        "Respondé preguntas sobre alumnos. Usá las herramientas para obtener "
        "los datos. No inventes datos que no estén en una ficha."
    ),
)


# Herramientas: funciones que el modelo puede pedir que se ejecuten.
# Al llamar al modelo, pydantic-ai le envía una descripción de cada herramienta
# (esquema): nombre, descripción y parámetros. El parámetro `ctx` no se incluye
# en el esquema, porque lo completa pydantic-ai con las dependencias (Deps) y
# no lo decide el modelo. Para buscar_alumno, el modelo solo ve `nombre`.
# @agent.tool registra la función como herramienta del agente.
@agent.tool
def listar_alumnos(ctx: RunContext[Deps]) -> list[str]:
    """Lista los alumnos que tienen ficha.

    Usar esta herramienta cuando no se conoce el nombre exacto de un alumno,
    o para saber qué alumnos existen antes de llamar a buscar_alumno.

    Args:
        ctx (RunContext[Deps]): Contexto de la ejecución. Entrega las
            dependencias: en ctx.deps.directorio está el directorio con las
            fichas. No forma parte del esquema que recibe el modelo.

    Returns:
        list[str]: Nombre completo de cada alumno, por ejemplo
        ["Juan Pérez", "María Gómez"].
    """
    nombres = listar_fichas(ctx.deps.directorio)
    logger.info("Herramienta listar_alumnos -> %d alumnos", len(nombres))
    return nombres

# Otra herramienta
@agent.tool
def buscar_alumno(ctx: RunContext[Deps], nombre: str) -> str:
    """Devuelve la ficha de un alumno.

    La ficha contiene nombre, edad, carrera y promedio. Si el nombre no
    corresponde a ninguna ficha, la herramienta pide al modelo que reintente.

    Args:
        ctx (RunContext[Deps]): Contexto de la ejecución. Entrega las
            dependencias: en ctx.deps.directorio está el directorio con las
            fichas. No forma parte del esquema que recibe el modelo.
        nombre (str): Nombre completo del alumno, por ejemplo "Juan Pérez".
            Se ignoran las mayúsculas y las tildes.

    Returns:
        str: Contenido de la ficha en formato Markdown.

    Raises:
        ModelRetry: Si no existe una ficha para ese nombre.
    """
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
    """Crea el modelo de OpenRouter con la clave de API del entorno.

    El identificador del modelo se toma de la constante MODELO. La clave se
    lee de la variable de entorno OPENROUTER_API_KEY, que load_dotenv carga
    desde el archivo .env.

    Returns:
        OpenRouterModel: Modelo listo para pasar al argumento `model` de
        agent.run_sync.

    Raises:
        SystemExit: Si la variable OPENROUTER_API_KEY no está definida o está
            vacía. El mensaje indica qué variable falta.
    """
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise SystemExit("Falta la variable de entorno OPENROUTER_API_KEY.")
    return OpenRouterModel(MODELO, provider=OpenRouterProvider(api_key=api_key))


def main() -> None:
    """Ejecuta el agente con la pregunta hardcodeada y registra el resultado.

    Pasos: configura el logging, envía PREGUNTA al agente con el directorio
    de fichas como dependencia, y registra los mensajes intercambiados (nivel
    DEBUG), el uso de tokens y la respuesta validada (nivel INFO).

    Returns:
        None: El resultado se registra en el log, no se devuelve.
    """
    configurar_logging(AQUI / "clase_agentes.log")
    logger.info("Pregunta: %s", PREGUNTA)
    logger.info("Modelo: %s", MODELO)

    # Se crea el modelo y se ejecuta el agente en forma síncrona.
    # run_sync espera a que termine, a diferencia de run, que es asíncrono.
    # El resultado es un objeto que contiene la respuesta y otra información.
    result = agent.run_sync(
        PREGUNTA,
        model=crear_modelo(),
        deps=Deps(directorio=AQUI / "fichas"),
    )

    # Se itera sobre todos los mensajes intercambiados (usuario, asistente, herramientas)
    # y se registra cada uno en el log.
    for mensaje in result.all_messages():
        logger.debug("Mensaje: %r", mensaje)
    # Se registra el uso de tokens y la respuesta validada.
    logger.info("Uso: %s", result.usage)
    logger.info("Respuesta: %s", result.output)


if __name__ == "__main__":
    main()
