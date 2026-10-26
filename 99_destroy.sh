#!/usr/bin/env bash
# Autor: David Vaquero <pepesan@gmail.com>
# Licencia: GPL-3.0-only
# Detiene y elimina los contenedores. Por defecto conserva los datos (./data/mongodb o MONGO_DATA_DIR).
# Usar --purge-data para borrar también el volumen bind (irreversible).
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

DATA_DIR="${MONGO_DATA_DIR:-./data/mongodb}"

docker compose down

if [ "${1:-}" = "--purge-data" ]; then
  read -r -p "Esto borrará $DATA_DIR de forma irreversible. ¿Continuar? [y/N] " confirm
  if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
    rm -rf "$DATA_DIR"
    echo "$DATA_DIR eliminado."
  else
    echo "Cancelado, datos conservados."
  fi
else
  echo "Contenedores eliminados. Datos conservados en $DATA_DIR (usa --purge-data para borrarlos)."
fi
