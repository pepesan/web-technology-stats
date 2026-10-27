# reports-blog

Datos agregados de la serie 2 del blog («dominios `.es` del registro oficial de Red.es», 27-10-2026). **Solo recuentos por tecnología:
ningún dominio, ningún titular.** No son parte del dashboard ni de la imagen `pepesan/web-stats` (por eso no están en `reports/`).

| Fichero | Qué es | Cómo se generó |
|---|---|---|
| `solapes-fuentes.txt` | Dominios por combinación de listados de origen (Tranco, Common Crawl, RISP 2020, RISP 2026) y cuántos se analizaron | `uv run webtechstats sources --batch 1` |
| `resumen-risp2026.txt` | Resumen del RISP 2026 y motivos de fallo (clase del último error de la petición) | `uv run webtechstats stats --batch 1 --source risp2026 --top 1` |
| `gob-es/`, `edu-es/`, `org-es/`, `com-es/`, `nom-es/` | Informe completo (`top-all.json`) de cada sufijo de segundo nivel dentro del RISP 2026 | `uv run --project dashboard wts-export-report --batch 1 --id gob-es --year 2026 --source risp2026 --tld gob.es --scope gob-es --no-cuts --out reports-blog` |
| `index.json` | Índice de esos informes | lo escribe `wts-export-report` |

Las gráficas de la serie salen de aquí y de `reports/` con `uv run python scripts/generate_blog_charts.py --serie es`.

Los datos salen del lote 1 de MongoDB tras el escaneo de octubre de 2026 y el etiquetado de fuentes (`webtechstats tag-sources`).
Con el listado RISP de otra fecha, o con otro escaneo, las cifras cambian.
