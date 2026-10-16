# Clase: agente con pydantic-ai, herramientas y logging

Este proyecto contiene, en el directorio `clase_agentes/`, un script que responde la pregunta `¿Qué promedio tiene Juan Pérez?` con un agente de pydantic-ai. El agente consulta una base de conocimiento local de 5 fichas de alumnos y devuelve una respuesta tipada.

## Flujo del agente

1. El script envía la pregunta al modelo.
2. El modelo decide llamar a la herramienta `buscar_alumno` con el argumento `nombre="Juan Pérez"`.
3. pydantic-ai ejecuta la herramienta. La herramienta lee la ficha `fichas/juan_perez.md` y devuelve su contenido al modelo.
4. El modelo arma la respuesta final.
5. pydantic-ai valida la respuesta contra la clase `RespuestaAlumno` (`nombre`, `carrera`, `promedio`). Si la validación falla, pydantic-ai pide al modelo que corrija la respuesta.

## Archivos

| Archivo (en `clase_agentes/`) | Contenido |
|---|---|
| `agente.py` | Script principal: modelo de salida, dependencias, agente, herramientas |
| `fichas.py` | Búsqueda de fichas en el directorio (prevención de path traversal) |
| `config_logging.py` | Configuración de logging con la biblioteca estándar |
| `fichas/*.md` | 5 fichas de alumnos con nombre, edad, carrera y promedio |
| `test_agente.py` | Pruebas sin red, con un modelo simulado |

## Ejecución

1. Crear el entorno virtual en la raíz del proyecto e instalar las dependencias: `uv venv .venv && uv pip install -r clase_agentes/requirements.txt`
2. Escribir la clave de API de OpenRouter en `clase_agentes/.env` (variable `OPENROUTER_API_KEY`). El script carga ese archivo con `python-dotenv`. El archivo `.env` está excluido del repositorio por `.gitignore`.
3. Ejecutar: `python agente.py`
4. Revisar el archivo `clase_agentes.log`, que contiene el nivel DEBUG.

El identificador del modelo es `anthropic/claude-haiku-5.5`. No fue verificado contra el catálogo de OpenRouter. La variable de entorno `OPENROUTER_MODEL` lo reemplaza sin editar el código.

## Dependencias de pydantic-ai (`deps_type`)

**Definición.** Una dependencia es un dato que una herramienta necesita para trabajar y que debe decidir el programador, no el modelo. En este proyecto, la dependencia es el directorio de las fichas.

### Constante global frente a dependencia

Con una constante global, la herramienta lee una variable definida al principio del archivo:

```python
DIRECTORIO = Path("fichas")

@agent.tool_plain
def buscar_alumno(nombre: str) -> str:
    return buscar_ficha(DIRECTORIO, nombre)
```

La herramienta queda atada a ese valor. Para probarla con otro directorio hay que modificar el código.

Con una dependencia, el programador entrega el directorio en el momento de ejecutar el agente. La herramienta lo recibe como parámetro.

### Pasos

1. **Definir el tipo de la dependencia.** Es una clase con los datos que la herramienta necesita:

   ```python
   @dataclass(frozen=True)
   class Deps:
       directorio: Path
   ```

2. **Declarar el tipo en el agente.** El parámetro `deps_type` informa qué clase de dependencia recibe el agente:

   ```python
   agent = Agent(deps_type=Deps, output_type=RespuestaAlumno)
   ```

3. **Pedir la dependencia en la herramienta.** El primer parámetro se llama `ctx` y tiene el tipo `RunContext[Deps]`. `RunContext` es el objeto que pydantic-ai crea en cada ejecución y que contiene las dependencias. Se usa el decorador `@agent.tool`; la variante `@agent.tool_plain` es para herramientas sin dependencias:

   ```python
   @agent.tool
   def buscar_alumno(ctx: RunContext[Deps], nombre: str) -> str:
       ficha = buscar_ficha(ctx.deps.directorio, nombre)
       ...
   ```

4. **Entregar el valor al ejecutar.** El argumento `deps` de `run_sync` recibe una instancia de `Deps`:

   ```python
   agent.run_sync(PREGUNTA, model=..., deps=Deps(directorio=AQUI / "fichas"))
   ```

### Qué ve el modelo

El modelo recibe el esquema de la herramienta con un solo parámetro, `nombre`. El parámetro `ctx` no aparece en ese esquema. El modelo no puede ver ni modificar el directorio.

### Ventajas

| Con constante global | Con dependencia |
|---|---|
| El directorio está fijo en el código | El directorio se decide en `run_sync` |
| Una prueba necesita editar el archivo | Una prueba pasa `Deps(directorio=...)` |
| El agente y los datos están mezclados | El agente y los datos están separados |

El modelo decide qué argumentos pasar a la herramienta. El programador decide con qué datos trabaja la herramienta. El argumento `deps` es el canal para esos datos.

## Cómo conoce el agente sus herramientas

Las herramientas se registran con el decorador `@agent.tool`. No existe una lista de herramientas que se pase al agente.

### 1. Registro (al importar el módulo)

El decorador se ejecuta cuando Python define la función:

```python
@agent.tool
def buscar_alumno(ctx: RunContext[Deps], nombre: str) -> str:
```

El decorador guarda la función en el objeto `agent`. Para construir la descripción de la herramienta, pydantic-ai lee tres elementos de la función:

| Elemento leído | Se usa para |
|---|---|
| Nombre de la función | Nombre de la herramienta: `buscar_alumno` |
| Docstring | Descripción de la herramienta y de cada parámetro |
| Anotaciones de tipo (`nombre: str`) | Tipo de cada parámetro |

El parámetro `ctx` se excluye. pydantic-ai lo identifica por su anotación `RunContext[Deps]`.

### 2. Envío al modelo (en cada ejecución)

`agent.run_sync` envía al modelo la pregunta junto con la descripción de cada herramienta registrada. Esa descripción se llama esquema (JSON Schema). Para `buscar_alumno`:

```
{'properties': {'nombre': {'description': 'Nombre completo del alumno, ...', 'type': 'string'}}, 'required': ['nombre'], 'type': 'object'}
```

El banner de pydantic-ai muestra la cantidad de herramientas registradas al arrancar: `tools: 2`.

### 3. Llamada (el modelo decide)

1. El modelo responde con una solicitud: llamar a `buscar_alumno` con `nombre='Juan Pérez'`. El modelo no ejecuta nada.
2. pydantic-ai valida los argumentos contra el esquema.
3. pydantic-ai ejecuta la función real y le pasa `ctx` con las dependencias.
4. pydantic-ai envía el valor devuelto al modelo en una segunda request.

El log de una ejecución real lo muestra: 2 requests al modelo y una línea `Herramienta buscar_alumno(nombre='Juan Pérez')` entre ambas.

### Consecuencia

El modelo conoce una herramienta solo por su nombre, su docstring y sus tipos. La calidad de la docstring afecta cuándo y cómo el modelo usa la herramienta.

## Información sensible y el archivo `.env`

Una clave de API no debe escribirse en el código. Un valor escrito en el código queda en el historial de git y en cada copia del repositorio, y en un repositorio público cualquiera puede usarlo. Una clave expuesta debe revocarse y reemplazarse.

El proyecto separa el código de la configuración:

1. `clase_agentes/.env` contiene los valores: `OPENROUTER_API_KEY` y `OPENROUTER_MODEL`.
2. `.gitignore` excluye `.env`, así que git no lo sube al repositorio.
3. `agente.py` carga el archivo con `load_dotenv(AQUI / ".env")` y lee los valores con `os.environ`.
4. Si falta la clave, `crear_modelo()` termina con el mensaje `Falta la variable de entorno OPENROUTER_API_KEY.`

Cada persona que clona el repositorio crea su propio `.env` con su propia clave.

## Salida tipada

`RespuestaAlumno` es un modelo de Pydantic. El parámetro `output_type=RespuestaAlumno` obliga al modelo a entregar `nombre`, `carrera` y `promedio`. El campo `promedio` es un `float` entre 0 y 10. Si el modelo entrega un valor fuera de ese rango, pydantic-ai reintenta (hasta `retries=2`).

## Reintento con `ModelRetry`

Si `buscar_alumno` no encuentra la ficha, lanza `ModelRetry` con un mensaje. pydantic-ai envía ese mensaje al modelo, y el modelo vuelve a llamar a la herramienta con otro argumento. El mensaje sugiere llamar a `listar_alumnos`.

## Seguridad de la ruta (path traversal)

Path traversal es un ataque que usa secuencias como `../` para leer archivos fuera del directorio previsto.

Versión insegura, que construye la ruta con el texto del modelo:

```python
ruta = directorio / f"{nombre}.md"   # nombre = "../../.env" sale del directorio
```

Versión segura, implementada en `fichas.py`: el texto del modelo se usa solo como clave de búsqueda entre los archivos que existen.

```python
def _indice(directorio):
    return {normalizar(f.stem): f for f in directorio.glob("*.md")}

ficha = _indice(directorio).get(normalizar(nombre))
```

El texto del modelo nunca forma parte de una ruta. La prueba `test_buscar_ficha_no_sale_del_directorio` lo verifica.

## Logging con la biblioteca estándar

El módulo `logging` tiene la misma arquitectura que log4j.

| log4j | `logging` | En este proyecto |
|---|---|---|
| Logger | `logging.getLogger(nombre)` | `clase_agentes.agente`, `fichas` |
| Appender | Handler | `StreamHandler` (consola), `FileHandler` (archivo) |
| Layout | Formatter | `%(asctime)s \| %(levelname)-7s \| %(name)s \| %(message)s` |
| Level | Nivel | Consola: INFO. Archivo: DEBUG |

Qué se registra:

* INFO: la pregunta, el modelo, cada llamada a herramienta con sus argumentos, el uso de tokens (`result.usage`) y la respuesta.
* WARNING: una ficha no encontrada.
* DEBUG: la secuencia completa de mensajes (`result.all_messages()`) y la ficha leída.

## Pruebas

```
pytest
```

Las pruebas no usan red. `FunctionModel` simula al modelo: llama a `buscar_alumno` y luego entrega la salida final.
