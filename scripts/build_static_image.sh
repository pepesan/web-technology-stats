#!/usr/bin/env bash
# Autor: David Vaquero <pepesan@gmail.com>
# Licencia: GPL-3.0-only
# Construye la imagen estática pepesan/web-stats (nginx + frontend + informes de ./reports).
# Uso: ./scripts/build_static_image.sh [TAG] [--push]
#   TAG     etiqueta de la imagen (por defecto, la fecha AAAAMMDD); siempre se etiqueta también "latest".
#   --push  sube ambas etiquetas a Docker Hub (hay que haber hecho antes `docker login`).
# Los informes se generan antes con: uv run --project dashboard wts-export-report --batch N --id AÑO --out reports
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

IMAGE="pepesan/web-stats"
TAG="$(date +%Y%m%d)"
PUSH=0
for arg in "$@"; do
    case "$arg" in
        --push) PUSH=1 ;;
        *) TAG="$arg" ;;
    esac
done

if [ ! -f reports/index.json ]; then
    echo "Error: falta reports/index.json; genera antes el informe con wts-export-report (ver cabecera del script)." >&2
    exit 1
fi

docker build -f docker/static/Dockerfile -t "$IMAGE:$TAG" -t "$IMAGE:latest" .
if [ "$PUSH" = 1 ]; then
    docker push "$IMAGE:$TAG"
    docker push "$IMAGE:latest"
fi
