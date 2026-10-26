#!/usr/bin/env bash
# Autor: David Vaquero <pepesan@gmail.com>
# Licencia: GPL-3.0-only
# Prueba E2E (Playwright + Chrome) de la imagen estática pepesan/web-stats en escritorio y móvil.
# Levanta un contenedor efímero, lanza los tests de e2e/ y lo elimina siempre al terminar.
# Uso: ./scripts/e2e_image.sh [TAG]      (por defecto latest; PORT=18090 cambia el puerto local)
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

TAG="${1:-latest}"
PORT="${PORT:-18090}"
NAME="wts-e2e-$$"
cleanup() { docker rm -f "$NAME" >/dev/null 2>&1 || true; }
trap cleanup EXIT

docker run -d --name "$NAME" -p "127.0.0.1:${PORT}:8080" "pepesan/web-stats:${TAG}" >/dev/null
for _ in $(seq 1 30); do
    if curl -fs "http://127.0.0.1:${PORT}/config.json" >/dev/null; then break; fi
    sleep 1
done
curl -fs "http://127.0.0.1:${PORT}/config.json" >/dev/null || { echo "Error: el contenedor no responde" >&2; exit 1; }

cd e2e
npm ci --no-audit --no-fund
BASE_URL="http://127.0.0.1:${PORT}" npx playwright test
