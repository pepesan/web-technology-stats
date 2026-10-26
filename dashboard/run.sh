#!/usr/bin/env bash
# Autor: David Vaquero <pepesan@gmail.com>
# Licencia: GPL-3.0-only
# Arranca el dashboard (API FastAPI + frontend Vue compilado) en http://127.0.0.1:8000
# Uso: ./run.sh [--host H] [--port P]
#   Compila el frontend si falta frontend/dist (o con REBUILD=1).
#   Usa ../webtechstats.toml (o WEBTECHSTATS_CONFIG / variables MONGO_*) para conectar a MongoDB.
# Desarrollo con recarga: en una terminal `uv run wts-dashboard --reload`, en otra `cd frontend && npm run dev`.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

if [ -z "${WEBTECHSTATS_CONFIG:-}" ] && [ -f ../webtechstats.toml ]; then
  export WEBTECHSTATS_CONFIG="$PWD/../webtechstats.toml"
fi

if [ ! -d frontend/node_modules ]; then
  (cd frontend && npm install)
fi
if [ ! -f frontend/dist/index.html ] || [ "${REBUILD:-0}" = "1" ]; then
  (cd frontend && npm run build)
fi

exec uv run wts-dashboard "$@"
