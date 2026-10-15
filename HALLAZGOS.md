# Hallazgos

## 2026-10-15 — El logger `httpx2` no queda silenciado (RESUELTO)

* Estado: medido. En la ejecución real del script, la consola mostró `INFO | httpx2 | HTTP Request: POST https://openrouter.ai/api/v1/chat/completions "HTTP/1.1 200 OK"`.
* Causa probable (no verificada): pydantic-ai 2.56.0 usa un cliente HTTP cuyo logger se llama `httpx2`.
* `clase_agentes/config_logging.py` silencia `("httpx", "httpcore", "openai")`. El nombre `httpx2` no está en la lista, así que el comentario "para que no se mezclen los mensajes de log con los nuestros" no se cumple para esas líneas.
* Opciones: agregar `"httpx2"` a la lista, o dejar las líneas como ejemplo de mensajes de una biblioteca.
* Resolución: se agregó `"httpx2"` a la lista de `clase_agentes/config_logging.py` (commit `531b0c0`). Una ejecución real posterior mostró 0 líneas de `httpx2` en la consola.
