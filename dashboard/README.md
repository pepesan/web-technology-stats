# Dashboard

Servidor Python (FastAPI) + frontend Vue 3 (Vite) para visualizar los datos de `web-technology-stats`
por tema: lenguajes de back y de front, frameworks/librerías de back y de front, bases de datos y otras tecnologías.
Es un proyecto `uv` propio que depende del paquete `webtechstats` del directorio padre.

## Dos modos de datos (flag `source`)

El frontend lee `config.json` (junto a la página) y elige de dónde saca los datos:

| `source` | Datos | Selector | Necesita |
|---|---|---|---|
| `reports` (por defecto) | informes estáticos `reports/<id>/top-<N>.json` | «Informe» (por año) | solo ficheros estáticos |
| `api` | API FastAPI en vivo | «Lote» (+ «Todos los lotes») | MongoDB + este servidor |

Sin `config.json` se usa `reports`. `?source=api` o `?source=reports` en la URL fuerza un modo (útil para probar). El servidor FastAPI sirve su propio `/config.json` con `{"source":"api"}`.

## Informes estáticos

Un informe es la foto de un lote: un JSON por corte del ranking (`top-100.json`, `top-1000.json` … `top-1000000.json`, más `top-all.json`) con el resumen y el ranking completo de cada tema, y un `index.json` con los informes disponibles. Solo hay agregados (ningún dominio). Un año de 1M de sitios ocupa unos 800 KB (135 KB comprimido).

```bash
# desde la raíz del repo, con MongoDB arrancado
uv run --project dashboard wts-export-report --batch 1 --id 2026 --label "Tranco 2026 · mundo" --year 2026 --max-position 1000000 --out reports
```

`--max-position N` acota todo el informe (también «todos») a las posiciones ≤ N del ranking. El lote 1 contiene el Tranco (posiciones 1–1.000.000) y, a continuación, dominios `.es` añadidos fuera de él (posiciones > 1M); con `--max-position 1000000` el informe «mundo» es solo el Tranco.

Con `--source NOMBRE` se exporta un informe de **una fuente** (solo los dominios de ese listado, campo `Site.sources`; se rellena con `webtechstats tag-sources`, ver `CLI.md`) y `--scope X` es el valor con el que el selector lo identifica. Los de la serie actual: `--id 2026 --source tranco --scope all` (mundo = el ranking Tranco) y `--id 2026-es --source risp2026 --scope es` (España = registro oficial de Red.es, copia de 26-10-2026). Se omiten los cortes con menos de 30 sitios analizados. El `index.json` marca cada informe con `scope` y `source`, y el frontend muestra el selector **«Fuente»** (Mundo (Tranco) / España 2026 (Red.es)) cuando hay más de uno; al cambiar de fuente abre el informe del mismo año. Con la fuente España el selector «Nº de sitios» se oculta (el corte por posición del ranking mundial no tiene sentido); es igual en modo `api`, donde cada fuente pasa `source=tranco|risp2026` a la API. El listado de 2020 (`risp2020`) está etiquetado en la base solo para calcular altas y bajas, y no se ofrece en el selector: sus datos son de un escaneo de 2026 sobre dominios de 2020, no un estudio de 2020. `--tld es` sigue disponible como filtro por sufijo. En modo `api` cada consulta de una fuente grande puede tardar decenas de segundos, así que el frontend muestra un aviso de carga, bloquea los selectores en la primera carga e ignora las respuestas atrasadas de peticiones anteriores.

`--no-cuts` escribe solo `top-all.json`. Los informes por sufijo de segundo nivel de la serie del blog (`--tld gob.es --source risp2026 --no-cuts`) se generan en **`reports-blog/`**, no en `reports/`: así no aparecen en el selector «Fuente» ni en la imagen estática (que solo copia `reports/`).

Volver a exportar el mismo `--id` lo sustituye; ids distintos se acumulan en `index.json` (ordenados por año). Los informes se versionan en git (`reports/`): son lo único que no se regenera sin repetir el escaneo.

## Imagen Docker estática

`pepesan/web-stats` (nginx sin privilegios, usuario 101, puerto 8080 + frontend + `reports/`, sin Python ni MongoDB, ~64 MB):

```bash
./scripts/build_static_image.sh 2026          # construye pepesan/web-stats:2026 y :latest
./scripts/build_static_image.sh 2026 --push   # además las sube a Docker Hub (docker login previo)
docker run -d -p 8080:8080 pepesan/web-stats:latest   # http://localhost:8080
```

E2E (Playwright + Chrome, escritorio y móvil) contra la imagen en local: `./scripts/e2e_image.sh [TAG]` (levanta un contenedor efímero y lo elimina; tests en `e2e/`, capturas en `e2e/test-results/`).

`WTS_SOURCE` (`reports` por defecto, o `api`) se vuelca a `config.json` al arrancar el contenedor; cualquier otro valor cae en `reports`. Ficheros: `docker/static/{Dockerfile,nginx.conf,40-wts-config.sh}`.

```bash
./run.sh                 # compila el frontend si hace falta y sirve http://127.0.0.1:8000
./run.sh --port 8080
```

Conexión a MongoDB: `../webtechstats.toml` si existe (ver `../webtechstats.example.toml`), o `WEBTECHSTATS_CONFIG` / variables `MONGO_*`.

Desarrollo: `uv run wts-dashboard --reload` y, en otra terminal, `cd frontend && npm run dev` (proxy de `/api` a :8000).

Tests: `uv run pytest` (API, con mongomock) y `cd frontend && npm test` (Vitest + jsdom).

API: `GET /api/batches`, `/api/topics`, `/api/overview?batch=N`, `/api/topics/{tema}?batch=N&limit=15&category=...`. Ambos aceptan `source=NOMBRE` (solo los dominios de ese listado: `tranco`, `risp2026`, `risp2020`, `cc`), `tld=es` (solo dominios `.es`) y `max_position=N` para limitar el análisis a los N primeros sitios del ranking; el frontend lo ofrece como selector «Nº de sitios» (Top 100, 1k, 10k, 100k, 200k … 900k, 1M) y lo guarda en la URL (`?top=N`).
La clasificación tecnología → tema está en `src/webtechstats/topics.py`.
