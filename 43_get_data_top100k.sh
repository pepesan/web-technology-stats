#!/usr/bin/env bash
# Importa y escanea el top 100.000 de dominios (carga de datos por volumen creciente).
# Requiere MongoDB arrancado (./00_init.sh o ./01_launch.sh).
# Uso: ./43_get_data_top100k.sh [FICHERO_CSV] [LOTE]
#   LOTE  identificador de lote (por defecto 1); cada lote guarda sus propios resultados
#         sin sobrescribir los de otros lotes.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

LIMIT=100000
CSV_FILE="${1:-./top-1m.csv}"
BATCH="${2:-1}"
# Hilos simultáneos: WORKERS=N lo fuerza (RETRY_FAILED=1 reintenta los sitios que ya fallaron, hasta MAX_RETRIES=N veces); si no, se usa [scan] workers de la configuración (por defecto 4).
SCAN_ARGS=()
if [ -n "${WORKERS:-}" ]; then SCAN_ARGS+=(--workers "$WORKERS"); fi
if [ -n "${RETRY_FAILED:-}" ]; then SCAN_ARGS+=(--retry-failed); fi
if [ -n "${MAX_RETRIES:-}" ]; then SCAN_ARGS+=(--max-retries "$MAX_RETRIES"); fi

./30_import_data.sh "$LIMIT" "$CSV_FILE" "$BATCH"
uv run webtechstats scan --limit "$LIMIT" --batch "$BATCH" "${SCAN_ARGS[@]}"
uv run webtechstats stats --top 20 --batch "$BATCH"
