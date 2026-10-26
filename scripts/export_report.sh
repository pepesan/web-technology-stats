#!/usr/bin/env bash
# Autor: David Vaquero <pepesan@gmail.com>
# Licencia: GPL-3.0-only
# Exporta un lote de MongoDB como informe estático (JSON) en ./reports.
# Uso: ./scripts/export_report.sh LOTE ID [ETIQUETA] [AÑO]
#   p. ej. ./scripts/export_report.sh 1 2026 "Tranco 2026" 2026
# Requiere MongoDB arrancado. Después: ./scripts/build_static_image.sh [TAG] [--push]
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

if [ "$#" -lt 2 ]; then
    echo "Uso: $0 LOTE ID [ETIQUETA] [AÑO]" >&2
    exit 1
fi
BATCH="$1"
ID="$2"
ARGS=(--batch "$BATCH" --id "$ID")
if [ -n "${3:-}" ]; then ARGS+=(--label "$3"); fi
if [ -n "${4:-}" ]; then ARGS+=(--year "$4"); fi

uv run --project dashboard wts-export-report "${ARGS[@]}" --out reports
