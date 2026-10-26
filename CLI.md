# CLI `webtechstats`

```bash
uv run webtechstats [--config RUTA] COMANDO [opciones]
```

Cada comando abre y cierra su propia conexión a MongoDB, así que son independientes entre sí.

## Opción global

| Opción | Descripción |
|---|---|
| `--config RUTA` | Fichero TOML de configuración. Si no se indica: `WEBTECHSTATS_CONFIG`, `./webtechstats.toml`, `~/.config/webtechstats/config.toml` |
| `--log-level NIVEL` | `DEBUG`, `INFO`, `WARNING` o `ERROR` para el log a fichero (por defecto `[log] level`) |
| `--version` / `--help` | Versión / ayuda |

Cada ejecución escribe su log (con rotación, 5 MB × 5) en un fichero propio dentro de `logs/` (`logs/` está en `.gitignore`) cuyo nombre lleva el comando, el lote y la fecha y hora de lanzamiento, p. ej. `logs/webtechstats_scan_batch-1_2026-10-25_20-15-03.log` (`batch-all` si no se indica lote; `init-db` y `detect` no llevan lote): comando invocado, resumen de importación y escaneo, progreso cada 100 sitios y, con `DEBUG`, una línea por sitio.

## Configuración

Plantilla: `webtechstats.example.toml`.

| Sección | Clave | Variable de entorno | Defecto |
|---|---|---|---|
| `[mongo]` | `host` | `MONGO_HOST` | `localhost` |
| | `port` | `MONGO_PORT` | `27017` |
| | `db` | `MONGO_DB` | `webstats` |
| | `username` | `MONGO_USER` | `mongodbuser` |
| | `password` | `MONGO_PASSWORD` | `mongodbuser` |
| | `auth_source` | `MONGO_AUTH_SOURCE` | `admin` |
| | `max_pool_size` | `MONGO_MAX_POOL_SIZE` | `10` |
| `[scan]` | `workers` | `SCAN_WORKERS` | `4` |
| | `max_retries` | `SCAN_MAX_RETRIES` | `10` |
| `[log]` | `dir` | `WTS_LOG_DIR` | `logs` |
| | `level` | `WTS_LOG_LEVEL` | `INFO` |

**Prioridad:** parámetro de línea de comandos > variable de entorno > fichero > defecto. Un fichero inexistente, un TOML inválido, una clave desconocida o un `workers` que no sea un entero ≥ 1 terminan con un error claro (sin traza).

## Comandos

### `init-db`
Comprueba la conexión, crea los índices y migra el esquema antiguo (índice único solo por `url`) al actual `(url, batch)`. Sale con código 1 si no hay conexión.

### `import-sites --file CSV [--limit N] [--batch B]`
Importa `posición,dominio` como sitios pendientes del lote `B` (por defecto 1).
- Inserta por bloques (`insert_many`, `ordered=False`) y es **idempotente por lote**: lo ya importado en ese lote se omite.
- El mismo dominio puede importarse en otro lote; cada lote tiene sus propios resultados.
- Salida: `Leídos | Importados | Ya existentes (omitidos)`.

### `scan [--limit N] [--batch B] [--workers W] [--processes P] [--retry-failed] [--max-retries M]`
Escanea hasta `N` sitios pendientes (`finished=False`, por defecto 100) ordenados por posición.
- Para cada sitio prueba `https://`, `http://` y `https://www.` y se queda con la primera variante que responde.
- `--batch B` limita el escaneo a ese lote; sin él se recorren todos.
- **Reanudable y sin repetir trabajo.** Cada resultado se guarda en cuanto llega. Un sitio ya intentado en el lote, con éxito o sin él, no se vuelve a escanear, así que relanzar el mismo comando continúa donde se dejó. Con `SIGINT` (`Ctrl+C`) o `SIGTERM` termina los sitios en vuelo, guarda todo y sale con "Interrumpido"; una segunda señal aborta de inmediato.
- `--retry-failed` reintenta también los sitios que ya fallaron, y `--max-retries M` (por defecto 10) limita cuántas veces (solo tiene efecto con `--retry-failed`).
- Lee los pendientes en páginas por posición y mantiene como mucho `2 × workers` peticiones en vuelo: la memoria no crece con el tamaño del lote.
- `--workers W` fija las peticiones HTTP simultáneas. Sin él se usa `[scan] workers` (4 por defecto). Las escrituras en MongoDB las hace el hilo principal.
- `--processes P` reparte el trabajo en P procesos (cada uno con `W` hilos; sin él, `[scan] processes`, 1 por defecto). Un proceso Python no pasa de ~1 núcleo por el GIL: con 12 procesos × 32 hilos el top 1M va a unos 2.700 sitios/min. Los trozos se reparten por `position % P` y escriben su propio log (`..._shard-IofP_...`).
- Los sitios que no responden suman `retries` y pasan a "sin respuesta".
- Escribe en stderr los hilos usados y una línea de progreso cada 100 sitios; al final `Procesados | OK | Fallidos`.

Estados de un sitio dentro de un lote: **analizado** (`finished`, con resultado), **sin respuesta** (intentado sin éxito, `retries > 0`) y **pendiente** (nunca intentado, `retries = 0`); los tres suman el total.

### `stats [--top N] [--batch B]`
Totales (importados, finalizados, sin respuesta, pendientes, con tecnología) y ranking de las `N` tecnologías más frecuentes (por defecto 20). Sin `--batch` agrega todos los lotes, de modo que un dominio presente en dos lotes cuenta dos veces.

### `detect URL`
Detecta las tecnologías de una URL concreta sin tocar la base de datos. Código 1 si no responde.

## Ejemplos

```bash
uv run webtechstats init-db
uv run webtechstats import-sites --file top-1m.csv --limit 1000 --batch 2
uv run webtechstats scan --limit 1000 --batch 2               # 4 hilos (o los de [scan] workers)
uv run webtechstats scan --limit 1000 --batch 2 --workers 16  # fuerza 16
SCAN_WORKERS=8 uv run webtechstats scan --batch 2
uv run webtechstats stats --top 20 --batch 2
uv run webtechstats detect wordpress.org
```

## Informes estáticos (`wts-export-report`)

Comando aparte, del proyecto `dashboard/` (no del CLI `webtechstats`): guarda un lote como informe JSON estático para verlo sin base de datos.

```bash
uv run --project dashboard wts-export-report --batch 1 --id 2026 --label "Tranco 2026" --year 2026 --out reports
```

`--batch` y `--id` son obligatorios; `--label` (por defecto el id), `--year` (por defecto el actual), `--tld` (p. ej. `es`: solo esos dominios, informe de ámbito acotado) y `--out` (por defecto `./reports`) son opcionales. Escribe `<out>/<id>/top-<N>.json` por cada corte (100, 1k, 10k, 100k, 200k … 1M, solo los que caben en el lote) y `top-all.json`, y actualiza `<out>/index.json`. Ver [dashboard/README.md](dashboard/README.md).

Gráficas para el blog (SVG + PNG) a partir de esos informes, sin MongoDB:

```bash
uv run python scripts/generate_blog_charts.py --blog ~/WebstormProjects/blogv2
```

Escribe en `<blog>/src/content/blog/AAAA/MM/AAAA-MM-DD-<slug>/images/` (patrón año y mes) las imágenes de la serie definida en `scripts/generate_blog_charts.py`.
