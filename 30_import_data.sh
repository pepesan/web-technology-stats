#!/usr/bin/env bash
# Autor: David Vaquero <pepesan@gmail.com>
# Licencia: GPL-3.0-only
# Importa el listado de dominios a MongoDB (colección `site`).
# Uso: ./30_import_data.sh [LIMITE] [FICHERO_CSV] [BATCH]
#   LIMITE       nº máximo de filas a importar (vacío = todas, 1 millón)
#   FICHERO_CSV  por defecto ./top-1m.csv (formato Tranco: posicion,dominio)
#   BATCH        identificador de lote (por defecto 1)
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

LIMIT="${1:-}"
CSV_FILE="${2:-./top-1m.csv}"
BATCH="${3:-1}"

ARGS=(--file "$CSV_FILE" --batch "$BATCH")
if [ -n "$LIMIT" ]; then
  ARGS+=(--limit "$LIMIT")
fi

uv run webtechstats import-sites "${ARGS[@]}"
