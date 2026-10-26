# Dominios `.es`: de dónde sacarlos

El top 1M de Tranco solo contiene unos 5.600 dominios `.es`. Para estudiar España de forma más completa hacen falta
listas propias. Hay dos fuentes; ninguna se guarda en git: todo va a `data/dominios/` (carpeta ignorada por `/data/` en
`.gitignore` y por `.dockerignore`).

| | Common Crawl | Red.es (RISP) |
|---|---|---|
| Cobertura | **parcial**: dominios que el rastreador ha visto enlazados | **completa**: el registro oficial de `.es` |
| Tamaño | 739.229 dominios (lanzamiento jul–sep 2026) | 1.915.938 dominios (copia de enero de 2020) |
| Acceso | abierto y automático | por solicitud a Red.es |
| Datos personales | no (solo nombres de dominio) | **sí** (nombre e identificación del titular) |
| Actualización | trimestral | la que entregue Red.es |

## 1. Common Crawl (automático)

```bash
./scripts/descargar_dominios_es.sh            # → data/dominios/dominios-es.csv  (formato posicion,dominio)
SKIP_DOMINIOS_ES=1 ./00_init.sh               # 00_init.sh lo descarga solo; así se omite
```

`./00_init.sh` ejecuta ese script si la lista no existe (idempotente: si ya está, no se descarga; un fallo solo avisa,
no impide levantar MongoDB). Variables del script:

- `CC_RELEASE`: lanzamiento concreto (p. ej. `cc-main-2026-jul-aug-sep`); por defecto, **el más reciente que exista**
  (se sondean los trimestres hacia atrás desde hoy).
- `DOMINIOS_ES_MINIMO`: nº mínimo de dominios para dar la descarga por válida (1000 por defecto).
- `DOMINIOS_DIR`: carpeta de destino (`./data/dominios`).

Cómo funciona: Common Crawl publica en S3 (`s3://commoncrawl/projects/hyperlinkgraph/`, y por HTTPS en
`data.commoncrawl.org`) un grafo de enlaces a nivel de dominio. El fichero
`<lanzamiento>/domain/<lanzamiento>-domain-vertices.txt.gz` (0,9–1,4 GB) tiene una línea `id<TAB>nombre-invertido<TAB>hosts`
(`es.elpais`, no `elpais.es`) **ordenada por nombre invertido**. El script lo lee en streaming, se queda con `es.<nombre>` y
`es.{com,nom,org,gob,edu}.<nombre>` (los dominios registrables bajo `.es`), los da la vuelta, numera y **corta la lectura al
pasar de `es.*`**. Tarda unos minutos y no deja ficheros intermedios. Catálogo de lanzamientos:
<https://index.commoncrawl.org/web-graphs-index.html>.

Limitaciones: es una lista **parcial** (solo lo que el rastreador ha visto enlazado) y la «posición» es solo el orden
alfabético, no un ranking de tráfico. Frente a la lista de Red.es de 2020, solo el 23,1 % de aquellos dominios aparece
aquí; en cambio, 295.953 dominios de Common Crawl no estaban en esa copia de Red.es (registrados después o no incluidos).

Importar y escanear (lote aparte, para no mezclar con el del top 1M):

```bash
./30_import_data.sh "" ./data/dominios/dominios-es.csv 3        # lote 3
uv run webtechstats scan --limit 800000 --batch 3 --processes 12 --workers 32
uv run --project dashboard wts-export-report --batch 3 --id 2026-es-cc --label "España (.es) · Common Crawl" --year 2026 --out reports
```

## 2. Red.es: listado RISP (completo)

Red.es es el registro de los `.es`. Su listado de dominios para reutilización (RISP, Ley 37/2007 de reutilización de la
información del sector público) **no es de descarga libre**: hay que solicitarlo mediante un trámite de su sede electrónica
(«solicitud de acceso al listado de dominios RISP», en `sede.red.gob.es`; comprueba allí el procedimiento y las condiciones
vigentes) y aceptar sus condiciones de uso. Es la copia que se usó para el estudio de 2020: ~1,9 M de dominios con tres
columnas separadas por `|`: `NOMBRE_DOMINIO`, `NOMBRE_TITULAR`, `IDENTIFICACION`.

**Contiene datos personales** (nombre del titular y su CIF/NIF/NIE). Por eso:

- **No se versiona nunca**: se guarda en `data/dominios/RISP_OTROS.csv` (ignorado por git y por Docker) y `.gitignore`
  tiene además una regla específica para ese nombre.
- **No se importa a MongoDB tal cual**: para escanear solo hace falta el dominio. Se extrae esa columna y nada más:

```bash
awk -F'|' 'NR > 1 { gsub(/"/, "", $1); print ++n "," tolower($1) }' \
  data/dominios/RISP_OTROS.csv > data/dominios/risp-es.csv
./30_import_data.sh "" ./data/dominios/risp-es.csv 4            # lote 4
```

Los informes que salen (`reports/`) son solo agregados por tecnología: no llevan dominios ni titulares.

Nota histórica: `legacy/importaSitiosSpain.py` espera el fichero `RISP_OTROS.csv` en su propio directorio; ya no está en el
repositorio (se retiró por contener datos personales). Si quieres usar ese script antiguo, copia allí tu copia local.

## Otras ideas (no automatizadas)

- Unir varios rankings abiertos (Majestic Million, Cisco Umbrella 1M, el propio Tranco) y quedarse con los `.es`: sube la
  cobertura de dominios con tráfico, pero cada lista es de ~1 M de entradas.
- Registros de transparencia de certificados (CT): dominios con certificado; muy voluminoso.
