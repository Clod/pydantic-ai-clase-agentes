# brainstorm: script pydantic-ai con logging

## Goal

Script Python didáctico para una clase. Enseña los conceptos básicos de IA agéntica con pydantic-ai: un agente recibe una pregunta, llama a una herramienta que recupera datos de una base de conocimiento local, y arma la respuesta final como salida tipada. Introduce además el logging estándar de Python.

## What I already know (decidido)

* Framework: pydantic-ai.
* Proveedor: OpenRouter. Identificador del modelo: `anthropic/claude-haiku-5.5` (decidido por el usuario; no verificado contra el catálogo de OpenRouter).
* Pregunta hardcodeada en el código: `¿Qué promedio tiene Juan Pérez?`
* Base de conocimiento: subdirectorio local con 5 fichas de alumnos en formato `.md`.
* Logging: módulo `logging` de la biblioteca estándar (decidido).

## Requirements

1. Herramienta `buscar_alumno(nombre)`: devuelve el contenido de la ficha `.md` del alumno. Si no existe la ficha, lanza `ModelRetry`.
2. Herramienta `listar_alumnos()`: devuelve los nombres disponibles.
3. La herramienta `buscar_alumno` no construye la ruta con el texto que envía el modelo. Busca el nombre entre los archivos listados del subdirectorio (prevención de path traversal). La lógica queda encapsulada en una función `buscar_ficha(directorio, nombre)` de un módulo aparte, para que la clase explique el concepto en una frase y muestre el detalle solo si el tiempo alcanza.
4. La ruta del subdirectorio llega al agente como dependencia (`deps_type` + `RunContext`), no como constante global.
5. Salida tipada: `output_type` es un modelo Pydantic `RespuestaAlumno` con los campos `nombre`, `carrera` y `promedio`, validado por pydantic-ai.
6. Logging con `logging`: handler de consola en nivel INFO, handler de archivo en nivel DEBUG, formatter con marca de tiempo, nivel y nombre del logger.
7. Se registra cada llamada a herramienta con sus argumentos, el uso de tokens (`result.usage`) y la secuencia de mensajes (`result.all_messages()`).
8. Clave de API de OpenRouter leída desde variable de entorno, nunca escrita en el código.

## Acceptance Criteria

- [ ] El script ejecutado con la pregunta hardcodeada imprime una respuesta que cumple el modelo Pydantic de salida.
- [ ] El log de consola muestra al menos una llamada a `buscar_alumno` con su argumento.
- [ ] El archivo de log contiene nivel DEBUG, incluida la secuencia de mensajes.
- [ ] Una ficha inexistente provoca un reintento visible en el log (`ModelRetry`).
- [ ] Un nombre con `../` no lee ningún archivo fuera del subdirectorio.
- [ ] No existe ninguna clave de API en el repositorio.

## Out of Scope

* Interfaz de usuario, entrada de preguntas por consola, historial entre ejecuciones.
* Búsqueda semántica o embeddings.
* Logfire / OpenTelemetry.

## Open Questions

* Verificar el identificador `anthropic/claude-haiku-5.5` en el catálogo de OpenRouter.
* Tipo del campo `promedio` (`float`) y formato de las fichas `.md` (por definir al crearlas).

## Technical Notes

* PRD significa Product Requirements Document (documento de requisitos del producto).
* Estado: requisitos decididos por el usuario el 2026-10-15; los campos de la salida tipada están abiertos.
