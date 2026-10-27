# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Estado del repositorio

La reestructuración (de scripts sueltos en la raíz a un paquete `src/webtechstats` con CLI, tests y dashboard) está hecha. **Lee `PLAN.md` antes de hacer nada**: contiene qué está hecho y qué queda pendiente, y debe mantenerse actualizado conforme avances. Documentación de usuario: `README.md`, `CLI.md` y `dashboard/README.md`.

- `src/webtechstats/` — paquete soportado, instalable vía `uv`. Es el único código de la herramienta que debe seguir creciendo.
- `dashboard/` — proyecto `uv` propio (FastAPI + frontend Vue 3 con Vite) que depende del paquete anterior vía `[tool.uv.sources]`. Se levanta como servicio `dashboard` de `compose.yaml` o con `dashboard/run.sh`. El frontend tiene un flag `source` (`config.json`): `reports` (por defecto, informes JSON estáticos de `reports/`, sin BBDD) o `api` (FastAPI en vivo); ambos pasan por la misma interfaz de `frontend/src/sources.js`. `wts-export-report` genera los informes y `./scripts/build_static_image.sh [TAG] [--push]` la imagen `pepesan/web-stats`.
- `legacy/` — scripts originales del proyecto (anteriores a la reestructuración), autocontenidos con su propia copia de `data/`. Siguen siendo funcionales pero no se desarrollan más; no muevas código nuevo ahí.

## Comandos

Gestión del entorno (usa `uv`, no pip/venv manual):
```bash
uv sync              # instala/actualiza dependencias (incluye dev: pytest, mongomock, responses)
uv run webtechstats --help
```

MongoDB (Docker, bind mount en `./data/mongodb`, gitignorado):
```bash
./00_init.sh          # primer arranque: crea ./data/mongodb, levanta compose.yaml, espera healthcheck
./01_launch.sh        # arranques posteriores (requiere que 00_init.sh ya se haya ejecutado); si hay backup en data/backups/ y la base está vacía, carga el más reciente (SKIP_RESTORE=1 lo omite)
./99_destroy.sh        # docker compose down, conserva los datos
./99_destroy.sh --purge-data   # además borra ./data/mongodb (pide confirmación)
```

Tests:
```bash
./10_test.sh                          # pytest tests/ -v
./10_test.sh -k nombre_test           # un test concreto
uv run pytest tests/test_x.py::test_y # alternativa directa
```
Los tests no requieren MongoDB real (usan `mongomock`) ni red real (usan `responses`/fixtures HTML locales). El dashboard tiene los suyos: `cd dashboard && uv run pytest` (API) y `cd dashboard/frontend && npm test` (Vitest). Flujo de trabajo: definir la funcionalidad, escribir primero los tests, implementar y validar; después, prueba real contra MongoDB.

Configuración: el CLI lee `webtechstats.toml` (plantilla `webtechstats.example.toml`; el real está gitignorado porque lleva credenciales — no leerlo con herramientas). Prioridad: parámetro de CLI > variable de entorno > fichero > defecto.

Carga de datos por volumen creciente (requieren MongoDB arrancado):
```bash
./30_import_data.sh [LIMITE] [FICHERO_CSV] [BATCH]   # importador genérico; por defecto ./top-1m.csv, todas las filas
./40_get_data_top10.sh [CSV] [LOTE]     # importa + escanea + stats; lo mismo 41 (1k), 42 (10k), 43 (100k) y 50 (1M)
WORKERS=10 ./41_get_data_top1k.sh       # fuerza N hilos; sin WORKERS manda [scan] workers (4 por defecto)
```
Los volúmenes grandes tardan horas: lanzarlos en segundo plano con el log redirigido a `logs/` (gitignorado).

CLI (comandos equivalentes, documentados con detalle en `CLI.md`):
```bash
uv run webtechstats init-db
uv run webtechstats import-sites --file top-1m.csv --limit 1000 --batch 2
uv run webtechstats scan --limit 100 --batch 2 --workers 10   # --workers/--batch opcionales
uv run webtechstats stats --top 20 --batch 2
uv run webtechstats detect wordpress.org   # detección puntual sin tocar la BBDD
```

## Arquitectura

Flujo de datos: `top-1m.csv` (lista Tranco de dominios, formato `posicion,dominio`, sustituto moderno de Alexa top-1m) → `import-sites` inserta cada dominio como un `Site` en MongoDB (`finished=False`) → `scan` recorre los `Site` pendientes, pide la página por HTTP y aplica el motor de detección → el resultado (lista de tecnologías) se guarda en `Site.tech` y se marca `finished=True` → `stats` agrega la colección con el pipeline de Mongo (`$unwind` + `$group`) para el ranking de tecnologías.

Módulos de `src/webtechstats/`:
- `config.py` — `MongoConfig` (`[mongo]`) y `ScanConfig` (`[scan] workers`, defecto 4), leídas de fichero TOML + variables de entorno (`MONGO_*`, `SCAN_WORKERS`); valores por defecto coherentes con `compose.yaml`. Errores de configuración → `ConfigError` (el CLI lo muestra sin traza).
- `db.py` — conexión perezosa a mongoengine (`init_db`/`close_db`/`ping`). Importante: **nada se conecta a import time**, solo cuando el CLI invoca `init_db()` explícitamente — así los módulos son importables en tests sin red ni BBDD.
- `models.py` — único modelo `Site` (mongoengine `Document`): `url` + `batch` (clave única compuesta: cada lote/ejecución conserva sus propios resultados), `position`, `retries`, `tech` (lista), `finished`, `last_search_datetime`. `Site.ensure_schema()` migra el índice antiguo `url_1` al compuesto.
- `wappalyzer.py` — motor de detección (fork propio de python-Wappalyzer). Carga `data/apps.json` (reglas por regex sobre URL/headers/script/meta/html, con `implies` para tecnologías derivadas) relativo a la ubicación del propio fichero del paquete, no al cwd.
- `importer.py` — lee el CSV y hace `insert_many` en bloques de `CHUNK_SIZE` filas, `ordered=False`, absorbiendo duplicados por el índice único `(url, batch)` (`BulkWriteError` con código 11000) para que sea idempotente y rápido a escala de 1M filas.
- `detection.py` — `detect_technologies(url)` prueba variantes `https://`, `http://`, `https://www.` en ese orden y devuelve la primera que responda; `scan_pending_sites` recorre `Site.objects(finished=False)` (opcionalmente de un `batch`) ordenado por `position` con un `limit`; con `workers` > 1 las peticiones HTTP van en un `ThreadPoolExecutor` (ventana de `2 × workers` en vuelo) y las escrituras en MongoDB las hace solo el hilo principal. Los pendientes se leen en páginas por posición y un sitio ya intentado en el lote (`retries > 0`) no se vuelve a escanear salvo con `retry_failed`; `should_stop` permite una parada ordenada (el CLI la engancha a SIGINT/SIGTERM) y relanzar continúa donde se dejó. Estados de un sitio: analizado (`finished`), sin respuesta (`retries > 0`), pendiente (`retries == 0`).
- `stats.py` — agregados Mongo puros (no cargan documentos a Python salvo el resultado final); `batch` opcional en todos; `batch_info()` resume cada lote.
- `topics.py` — `TopicClassifier`: tecnología → tema (lenguajes de back/front, frameworks y librerías de back/front, bases de datos, otras) a partir de las categorías de `apps.json` (`Site.tech` solo guarda nombres, así que reclasificar no obliga a re-escanear).
- `cli.py` — grupo `click` con `--config` global; cada subcomando abre su propia conexión (`init_db`) y la cierra al terminar (`close_db`), por eso los comandos son independientes entre sí y se pueden testear por separado.

`src/webtechstats/data/apps.json` se actualiza periódicamente desde el fork mantenido `enthec/webappanalyzer` (continuación de Wappalyzer tras su cierre en 2023), fusionando los fragmentos `src/technologies/*.json` + `src/categories.json` en el único fichero que espera `wappalyzer.py`. Al actualizarlo, comprobar que el merge sigue siendo compatible con el parser (mismas claves `url/html/script/headers/meta/implies/cats`, campos nuevos como `dom`/`js`/`cpe` se ignoran sin romper nada).

`top-1m.csv` se actualiza desde el Tranco list (tranco-list.eu), el sustituto estándar de Alexa top-1m: agrega tráfico real de Chrome UX Report, Umbrella, Majestic y Farsight.

## Procesos largos

**Todo proceso que pueda tardar (escaneos, cargas de datos, builds de imagen, benchmarks, tests largos...) se lanza siempre en segundo plano** (`run_in_background`) con la salida redirigida a un fichero de `logs/` (gitignorado), y se avisa de la ruta del log. Los logs que genero a mano siguen la misma convención que los del CLI: `logs/<accion>_batch-<N>_<AAAA-MM-DD>_<HH-MM-SS>.log` (acción, lote y fecha de lanzamiento), para localizarlos fácilmente. El propio CLI ya escribe su log así en `logs/webtechstats_<comando>_batch-<N|all>_<fecha>.log`. Así el usuario puede seguir dando órdenes mientras corre, y yo respondo "¿cómo va?" leyendo el log o consultando MongoDB. Nada de esperar en primer plano a que termine (ni con `tail --pid` o `sleep` encadenados): para esperar a algo hay que dejarlo encadenado dentro de otro comando en segundo plano.
- Los escaneos son reanudables: para cortarlos se manda `SIGTERM`/`SIGINT` al proceso (se guardan los sitios en vuelo); no hay que esperar a que acaben para atender otra petición.
- No reescribir un script `.sh` mientras se está ejecutando (bash lo lee de forma incremental y se rompe): sustituirlo con un fichero nuevo renombrado.

## Seguridad de datos y tests

- **Ningún test puede ejecutar un script destructivo (`99_destroy.sh --purge-data`, cualquier `rm -rf`) contra el repositorio real.** Los scripts hacen `cd` a su propio directorio, así que los tests los ejecutan siempre **copiados a un directorio temporal** (fixtures `sandbox` en `tests/test_infra.py` y `box` en `tests/test_init_download.py`), con `docker`/`curl` falsos en el `PATH`. Además, un test que escribo antes de la implementación («fase roja») no debe poder tocar datos reales ni siquiera mientras falla.
  - **Por qué:** el 2026-10-25 un test mío ejecutó el `99_destroy.sh --purge-data` real antes de que respetara `MONGO_DATA_DIR` y borró los ficheros de `./data/mongodb` (el 1M importado y los resultados del escaneo). Se perdió el trabajo de esa tarde; el contenedor cayó con segfault al recrearse sobre un journal huérfano.
- **Antes de encadenar una acción destructiva o un reinicio a «cuando termine el proceso X», comprobar que el PID es no vacío** (`[ -n "$PID" ]`): `tail --pid=` con un PID vacío vuelve de inmediato y la acción se ejecuta a destiempo. Reiniciar MongoDB mientras corre un escaneo o un benchmark lo rompe.
- `./00_init.sh` descarga `top-1m.csv` (Tranco) si falta; el fichero está en `.gitignore` y fuera del índice. También descarga la lista de dominios `.es` de Common Crawl a `data/dominios/` (ignorada; `SKIP_DOMINIOS_ES=1` la omite). **El listado RISP de Red.es lleva datos personales (titulares con CIF/NIF): nunca se versiona** (ver `docs/dominios-es.md`).

