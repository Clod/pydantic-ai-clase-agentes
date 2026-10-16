"""Pruebas sin red: un modelo simulado (FunctionModel) reemplaza a OpenRouter."""

import logging
from pathlib import Path

from pydantic_ai import ModelResponse, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from agente import Deps, RespuestaAlumno, agent
from fichas import buscar_ficha, listar_fichas
from registro_turnos import registrar_turnos

FICHAS = Path(__file__).parent / "fichas"
FINAL = {"nombre": "Juan Pérez", "carrera": "Licenciatura en Sistemas", "promedio": 8.4}


def test_buscar_ficha_ignora_tildes_y_mayusculas():
    assert "8.4" in buscar_ficha(FICHAS, "juan perez")


def test_buscar_ficha_inexistente_devuelve_none():
    assert buscar_ficha(FICHAS, "Nadie Nunca") is None


def test_buscar_ficha_no_sale_del_directorio():
    assert buscar_ficha(FICHAS, "../../AGENTS") is None
    assert buscar_ficha(FICHAS, "../fichas/juan_perez") is None


def test_listar_fichas_devuelve_cinco_nombres():
    nombres = listar_fichas(FICHAS)
    assert len(nombres) == 5
    assert "Juan Pérez" in nombres


def _modelo_simulado(nombres_a_buscar: list[str]) -> FunctionModel:
    """Crea un modelo simulado que llama a buscar_alumno y luego responde.

    Args:
        nombres_a_buscar (list[str]): Nombres que el modelo simulado pasa a
            buscar_alumno, uno por llamada y en orden.

    Returns:
        FunctionModel: Modelo que, una vez agotados los nombres, entrega la
        salida final FINAL.
    """
    pendientes = list(nombres_a_buscar)

    def respuesta(mensajes, info: AgentInfo) -> ModelResponse:
        if pendientes:
            nombre = pendientes.pop(0)
            return ModelResponse(parts=[ToolCallPart("buscar_alumno", {"nombre": nombre})])
        return ModelResponse(parts=[ToolCallPart("final_result", FINAL)])

    return FunctionModel(respuesta)


def test_agente_devuelve_respuesta_tipada():
    result = agent.run_sync(
        "¿Qué promedio tiene Juan Pérez?",
        model=_modelo_simulado(["Juan Pérez"]),
        deps=Deps(directorio=FICHAS),
    )
    assert result.output == RespuestaAlumno(**FINAL)


def test_agente_reintenta_si_la_ficha_no_existe():
    result = agent.run_sync(
        "¿Qué promedio tiene Juan Pérez?",
        model=_modelo_simulado(["Juan Perezz", "Juan Pérez"]),
        deps=Deps(directorio=FICHAS),
    )
    assert result.output.promedio == 8.4
    mensajes = repr(result.all_messages())
    assert "No existe una ficha" in mensajes


def test_registrar_turnos_escribe_un_turno_por_request(caplog):
    result = agent.run_sync(
        "¿Qué promedio tiene Juan Pérez?",
        model=_modelo_simulado(["Juan Pérez"]),
        deps=Deps(directorio=FICHAS),
    )
    with caplog.at_level(logging.INFO, logger="registro_turnos"):
        registrar_turnos(result.all_messages())
    lineas = [r.getMessage() for r in caplog.records]
    assert lineas[0].startswith("Turno 1 | pydantic-ai envía al modelo la pregunta")
    assert any("Turno 1 | el modelo pide ejecutar buscar_alumno" in l for l in lineas)
    assert any("Turno 2 | pydantic-ai envía al modelo el resultado de buscar_alumno" in l for l in lineas)
