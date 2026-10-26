#!/usr/bin/env bash
# Autor: David Vaquero <pepesan@gmail.com>
# Licencia: GPL-3.0-only
# Escanea con Trivy: vulnerabilidades, secretos, malas configuraciones y licencias.
# Uso: ./scripts/scan_trivy.sh                       código y dependencias del repo (uv.lock, package-lock.json, Dockerfiles)
#      ./scripts/scan_trivy.sh --image [IMAGEN]      imagen publicada (por defecto pepesan/web-stats:latest)
#   STRICT=1  sale con error si hay hallazgos HIGH o CRITICAL (por defecto solo informa).
# El informe se guarda en logs/trivy_<fs|image>_<fecha>.txt.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

if ! command -v trivy >/dev/null 2>&1; then
    echo "Error: no se encuentra trivy en el PATH (https://trivy.dev)." >&2
    exit 1
fi

MODE=fs
TARGET=.
if [ "${1:-}" = "--image" ]; then
    MODE=image
    TARGET="${2:-pepesan/web-stats:latest}"
fi

STRICT_ARGS=()
if [ "${STRICT:-0}" = 1 ]; then STRICT_ARGS=(--severity HIGH,CRITICAL --exit-code 1); fi

mkdir -p logs
REPORT="logs/trivy_${MODE}_$(date +%Y-%m-%d_%H-%M-%S).txt"
if [ "$MODE" = fs ]; then
    SCAN_ARGS=(fs --scanners vuln,secret,misconfig,license
        --skip-dirs .git,.venv,node_modules,logs,data/mongodb,reports,dist
        --skip-files top-1m.csv)
else
    SCAN_ARGS=(image --scanners vuln,secret)
fi

echo "Trivy ($MODE) → $REPORT"
set +e
trivy "${SCAN_ARGS[@]}" "${STRICT_ARGS[@]}" "$TARGET" 2>&1 | tee "$REPORT"
STATUS=${PIPESTATUS[0]}
set -e
exit "$STATUS"
