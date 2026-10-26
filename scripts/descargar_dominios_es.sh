#!/usr/bin/env bash
# Autor: David Vaquero <pepesan@gmail.com>
# Licencia: GPL-3.0-only
# Descarga la lista de dominios .es del grafo de dominios de Common Crawl (https://commoncrawl.org/web-graphs)
# y la guarda como `posicion,dominio` (formato de 30_import_data.sh). Es una lista PARCIAL: solo los dominios
# que el rastreador ha visto enlazados; para el listado completo hay que pedirlo a Red.es (docs/dominios-es.md).
#
# Uso: ./scripts/descargar_dominios_es.sh [DESTINO]
#   DESTINO              por defecto ./data/dominios/dominios-es.csv (carpeta ignorada por git)
#   CC_RELEASE           lanzamiento concreto (p. ej. cc-main-2026-apr-may-jun); por defecto, el más reciente que exista
#   DOMINIOS_ES_MINIMO   nº mínimo de dominios para dar la descarga por válida (por defecto 1000)
#   CC_BASE_URL          origen (por defecto https://data.commoncrawl.org/projects/hyperlinkgraph)
# Si el destino ya existe y no está vacío no se vuelve a descargar. El fichero de vértices pesa ~1 GB y se lee en
# streaming: se corta al pasar de las entradas `es.*` (están ordenadas por nombre invertido).
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

DEST="${1:-${DOMINIOS_DIR:-./data/dominios}/dominios-es.csv}"
BASE="${CC_BASE_URL:-https://data.commoncrawl.org/projects/hyperlinkgraph}"
MINIMO="${DOMINIOS_ES_MINIMO:-1000}"

if [ -s "$DEST" ]; then
  echo "$DEST ya existe ($(wc -l < "$DEST") dominios): no se descarga."
  exit 0
fi

vertices_url() { echo "$BASE/$1/domain/$1-domain-vertices.txt.gz"; }

# Lanzamiento: el indicado o el más reciente que exista (trimestres hacia atrás desde hoy).
release="${CC_RELEASE:-}"
if [ -z "$release" ]; then
  trimestres=("jan-feb-mar" "apr-may-jun" "jul-aug-sep" "oct-nov-dec")
  hoy="${DOMINIOS_ES_HOY:-now}"
  anio=$(date -d "$hoy" +%Y)
  q=$(( ($(date -d "$hoy" +%-m) - 1) / 3 ))
  for _ in $(seq 1 10); do
    candidato="cc-main-$anio-${trimestres[$q]}"
    if curl -fsI --max-time 30 "$(vertices_url "$candidato")" >/dev/null 2>&1; then
      release="$candidato"
      break
    fi
    q=$((q - 1))
    if [ "$q" -lt 0 ]; then q=3; anio=$((anio - 1)); fi
  done
fi
if [ -z "$release" ]; then
  echo "No se encontró ningún lanzamiento reciente del grafo de dominios en $BASE" >&2
  exit 1
fi
echo "Descargando dominios .es de Common Crawl ($release); puede tardar unos minutos..."

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
mkdir -p "$(dirname "$DEST")"

# curl recibirá SIGPIPE (23) cuando awk corte al pasar de `es.*`: se comprueban los estados a mano.
set +o pipefail
curl -fsL --retry 3 --retry-delay 2 "$(vertices_url "$release")" | gzip -dc | LC_ALL=C awk -F'\t' '
  $2 > "et" { exit }
  $2 ~ /^es\.[a-z0-9-]+$/ || $2 ~ /^es\.(com|nom|org|gob|edu)\.[a-z0-9-]+$/ {
    n = split($2, parts, "."); dominio = parts[n]
    for (i = n - 1; i >= 1; i--) dominio = dominio "." parts[i]
    print ++posicion "," dominio
  }' > "$work/dominios-es.csv"
estados=("${PIPESTATUS[@]}")
set -o pipefail

if { [ "${estados[0]}" != 0 ] && [ "${estados[0]}" != 23 ]; } || { [ "${estados[1]}" != 0 ] && [ "${estados[1]}" != 141 ]; }; then
  echo "La descarga de dominios .es falló (curl=${estados[0]}, gzip=${estados[1]})." >&2
  exit 1
fi
total=$(wc -l < "$work/dominios-es.csv")
if [ "$total" -lt "$MINIMO" ]; then
  echo "Descarga no válida: se esperaba al menos $MINIMO dominios .es y hay $total." >&2
  exit 1
fi
mv "$work/dominios-es.csv" "$DEST"
echo "Dominios .es guardados en $DEST ($total dominios, $release)."
