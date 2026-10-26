#!/usr/bin/env bash
# Autor: David Vaquero <pepesan@gmail.com>
# Licencia: GPL-3.0-only
# Arranca MongoDB si ya fue inicializado (directorio de datos existente: ./data/mongodb o MONGO_DATA_DIR).
# Usar 00_init.sh en el primer arranque.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

DATA_DIR="${MONGO_DATA_DIR:-./data/mongodb}"
if [ ! -d "$DATA_DIR" ]; then
  echo "No existe $DATA_DIR todavía. Ejecuta primero ./00_init.sh" >&2
  exit 1
fi

docker compose up -d
echo "MongoDB arrancado. Estado:"
docker compose ps
