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

Con `--tld es` se exporta un informe de **ámbito acotado** (solo dominios `.es` del lote, también los de fuera del Tranco), por ejemplo `--id 2026-es --tld es`. Se omiten los cortes con menos de 30 sitios analizados (los `.es` casi no llegan al Top 100/1k). El `index.json` marca cada informe con `scope` (`all` o el TLD) y el frontend muestra el selector **«Ámbito»** (Mundo / España (.es)) cuando hay más de uno; al cambiar de ámbito abre el informe del mismo año. Con un ámbito acotado el selector «Nº de sitios» se oculta (el corte por posición mundial no tiene sentido para los `.es`); es igual en modo `api`, donde «España» pasa `tld=es` a la API.

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

API: `GET /api/batches`, `/api/topics`, `/api/overview?batch=N`, `/api/topics/{tema}?batch=N&limit=15&category=...`. Ambos aceptan `tld=es` (solo dominios `.es`) y `max_position=N` para limitar el análisis a los N primeros sitios del ranking; el frontend lo ofrece como selector «Nº de sitios» (Top 100, 1k, 10k, 100k, 200k … 900k, 1M) y lo guarda en la URL (`?top=N`).
La clasificación tecnología → tema está en `src/webtechstats/topics.py`.
