# Estadísticas de tecnologías web

Herramientas para extraer y analizar las tecnologías que usan las principales webs de Internet: lenguajes, frameworks, bases de datos, servidores, CMS, analítica, etc. Salió de una idea de Andros Fenollosa en su artículo sobre el uso de WordPress en Internet: [Analizando un millón de páginas para saber cuánto se usa WordPress](https://programadorwebvalencia.com/analizando-un-millon-de-paginas-para-saber-cuanto-se-usa-wordpress-2019/).

## Cómo funciona

```
top-1m.csv ──import-sites──▶ MongoDB (colección site) ──scan──▶ tech por sitio ──stats / dashboard──▶ rankings
```

1. `import-sites` carga los dominios del CSV como sitios pendientes de un **lote** (`batch`).
2. `scan` pide cada página por HTTP (en paralelo) y le aplica el motor de detección (reglas de Wappalyzer). Es reanudable: se puede cortar en cualquier momento y relanzar sin repetir ningún sitio ya intentado.
3. `stats` y el **dashboard** agregan los resultados por tecnología y por tema.

## Dataset

`top-1m.csv` (gitignorado; lo descarga `./00_init.sh` si falta) es el [Tranco list](https://tranco-list.eu) (formato `posición,dominio`), el sustituto actual de Alexa top-1m: agrega tráfico real de Chrome UX Report, Umbrella, Majestic y Farsight. Las reglas de detección están en `src/webtechstats/data/apps.json` (fork mantenido [enthec/webappanalyzer](https://github.com/enthec/webappanalyzer), continuación de Wappalyzer).

## Puesta en marcha

Requisitos: Docker, [uv](https://docs.astral.sh/uv/) y Python 3.14 (uv lo descarga solo).

```bash
uv sync                      # dependencias del proyecto
./00_init.sh                 # primer arranque: MongoDB + dashboard (compose.yaml) y descarga top-1m.csv si falta
./40_get_data_top10.sh       # prueba rápida: importa y escanea los 10 primeros dominios
```

Después abre el dashboard en <http://127.0.0.1:8000>.

### Scripts

| Script | Qué hace |
|---|---|
| `00_init.sh` | Primer arranque: crea `./data/mongodb`, levanta `compose.yaml`, espera al healthcheck y descarga `top-1m.csv` (Tranco, `TRANCO_URL` para cambiar el origen) si no existe |
| `01_launch.sh` | Arranques posteriores |
| `99_destroy.sh [--purge-data]` | `docker compose down`; con `--purge-data` borra también `./data/mongodb` |
| `10_test.sh` | Tests del proyecto principal (`pytest`) |
| `30_import_data.sh [LIMITE] [CSV] [LOTE]` | Importador genérico |
| `40_` / `41_` / `42_` / `43_` / `50_get_data_top…sh [CSV] [LOTE]` | Importa y escanea el top 10 / 1k / 10k / 100k / 1M, y muestra el ranking |

Los scripts de carga aceptan el lote como segundo argumento (por defecto 1) y `WORKERS=N` para forzar el número de hilos. Los de 100k y 1M tardan de horas a días: lánzalos en segundo plano y con el log redirigido (`./43_get_data_top100k.sh > logs/43.log 2>&1 &`).

## Lotes (una ejecución = un lote)

Cada sitio se identifica por `(url, batch)`: el mismo dominio puede existir una vez por lote, y cada lote conserva sus propios resultados sin sobrescribir los de otros. `scan --batch N` y `stats --batch N` actúan solo sobre un lote; el dashboard tiene un selector de lote (o de informe, en modo estático).

## Configuración

El CLI lee un fichero TOML. Copia `webtechstats.example.toml` a `webtechstats.toml` (ignorado por git, puede llevar credenciales):

```toml
[mongo]
host = "localhost"
port = 27017
db = "webstats"
username = "mongodbuser"
password = "mongodbuser"
auth_source = "admin"
max_pool_size = 10 # conexiones máximas por proceso

[scan]
workers = 4        # peticiones HTTP simultáneas
max_retries = 10   # un sitio que falla 10 veces deja de reintentarse

[log]
dir = "logs"       # un log por ejecución: webtechstats_<comando>_batch-<N>_<fecha>.log
level = "INFO"
```

Se busca en `--config RUTA`, `WEBTECHSTATS_CONFIG`, `./webtechstats.toml` y `~/.config/webtechstats/config.toml`. Prioridad: **parámetro de CLI > variable de entorno (`MONGO_*`, `SCAN_WORKERS`) > fichero > valor por defecto**. Detalle de cada comando en [CLI.md](CLI.md).

## Infraestructura para escaneos grandes

- **MongoDB (`compose.yaml`).** El contenedor lleva `ulimits.nofile = 64000` (con el valor por defecto de 1024 solo admite unas 400 conexiones) y la caché de WiredTiger acotada a 4 GiB (la base ocupa cientos de MB). Cada proceso del CLI usa un pool de pymongo acotado (`max_pool_size`).
- **Datos fuera de Dropbox.** Si el repositorio vive dentro de `~/Dropbox`, define `MONGO_DATA_DIR=/ruta/fuera/de/dropbox/mongodb` antes de `./00_init.sh` / `./01_launch.sh` / `./99_destroy.sh`, para que Dropbox no sincronice los ficheros vivos de la base.
- **Kernel del host (opcional, necesita `sudo`).** `host/90-webtechstats.conf` ensancha los puertos efímeros (reservando los de servicios locales, como el 27017 de MongoDB), reutiliza sockets en `TIME_WAIT` y sube el límite de `conntrack`. Se ve el efecto sin aplicar nada con `./host/aplicar_sysctl.sh --dry-run`; se instala con `sudo ./host/aplicar_sysctl.sh` y se revierte con `sudo ./host/aplicar_sysctl.sh --revert`. Hoy no hace falta: es un seguro para escalar más de 10 veces.
- **Varios núcleos.** Los hilos de un proceso comparten el GIL y ocupan un solo núcleo; para usar más, `scan --processes P` reparte los sitios entre P procesos disjuntos, cada uno con `--workers` hilos.

## Dashboard

`dashboard/` es un proyecto uv propio: servidor FastAPI + frontend Vue 3. Muestra los resultados por tema (lenguajes de back y de front, frameworks y librerías de back y de front, bases de datos, otras tecnologías), con selector de lote, filtro por categoría, vista de tabla, el desglose analizados / pendientes / sin respuesta y un aviso mientras queden sitios por intentar. Se levanta con `compose.yaml` (puerto `DASHBOARD_PORT`, 8000 por defecto; solo en localhost salvo que `DASHBOARD_BIND` indique otra IP, p. ej. la de la LAN en un `.env` gitignorado; no tiene autenticación) o a mano con `dashboard/run.sh`. También funciona **sin base de datos**: `wts-export-report` guarda un lote como informe estático por año (`reports/`, versionado en git) y la imagen `pepesan/web-stats` (`./60_build_static_image.sh`) lo sirve con nginx; el modo lo decide el flag `source` de `config.json`. Ver [dashboard/README.md](dashboard/README.md).

## Tests

```bash
./10_test.sh                           # proyecto principal (mongomock y responses: sin MongoDB ni red reales)
cd dashboard && uv run pytest          # API del dashboard
cd dashboard/frontend && npm test      # frontend (Vitest)
```

## Estructura

```
src/webtechstats/   paquete: config, db, models, importer, detection, stats, topics, wappalyzer, cli
tests/              tests del paquete
dashboard/          servidor FastAPI + frontend Vue (proyecto uv propio, con su Dockerfile)
legacy/             scripts originales anteriores a la reestructuración (funcionales, sin desarrollo)
compose.yaml        MongoDB + dashboard
reports/            informes estáticos por año (JSON, generados con wts-export-report)
docker/static/      imagen estática pepesan/web-stats (nginx); 60_build_static_image.sh la construye
```

## Notas

- Con muchos elementos, MongoDB puede fallar al ordenar por falta de memoria; se resuelve ampliando el buffer de ordenación:
  `db.adminCommand({"setParameter": 1, "internalQueryExecMaxBlockingSortBytes": 934217728})`
  ([referencia](http://pe-kay.blogspot.com/2016/05/how-to-change-mongodbs-sort-buffer-size.html)).
- Ficha de la encuesta: para un millón de población, tener 500.000 sitios consultados supone un 50 % de muestra y un margen de error inferior al 0,1 %.
- Los escaneos grandes son pesados y pueden tardar de horas a varios días.

## Licencia

Licenciado bajo GPL v3.
David Vaquero <pepesan-at-gmail.com>
