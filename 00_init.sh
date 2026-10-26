#!/usr/bin/env bash
# Primer arranque: crea el directorio de datos (bind mount), levanta MongoDB en segundo plano,
# espera a que esté listo y descarga top-1m.csv (lista Tranco) si no lo tenemos. Idempotente.
#   MONGO_DATA_DIR  directorio de datos de MongoDB (por defecto ./data/mongodb)
#   TRANCO_URL      origen de la lista (por defecto https://tranco-list.eu/top-1m.csv.zip)
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

# Directorio de datos de MongoDB (bind mount). Cámbialo con MONGO_DATA_DIR para sacarlo de ~/Dropbox.
DATA_DIR="${MONGO_DATA_DIR:-./data/mongodb}"
mkdir -p "$DATA_DIR"

echo "Levantando MongoDB (compose.yaml)..."
docker compose up -d

echo "Esperando a que MongoDB esté listo (healthcheck)..."
ready=0
for i in $(seq 1 60); do
  status=$(docker inspect -f '{{.State.Health.Status}}' webtechstats-mongodb 2>/dev/null || echo "starting")
  if [ "$status" = "healthy" ]; then
    ready=1
    break
  fi
  sleep 2
done
if [ "$ready" -ne 1 ]; then
  echo "MongoDB no respondió a tiempo. Revisa: docker compose logs mongodb" >&2
  exit 1
fi
echo "MongoDB listo."

# top-1m.csv (gitignorado): se descarga solo si falta o está vacío.
CSV_FILE="./top-1m.csv"
TRANCO_URL="${TRANCO_URL:-https://tranco-list.eu/top-1m.csv.zip}"
if [ -s "$CSV_FILE" ]; then
  echo "top-1m.csv ya existe ($(wc -l < "$CSV_FILE") filas): no se descarga."
else
  echo "Descargando top-1m.csv de $TRANCO_URL ..."
  work="$(mktemp -d)"
  trap 'rm -rf "$work"' EXIT
  if ! curl -fsSL --retry 3 --retry-delay 2 -o "$work/top-1m.csv.zip" "$TRANCO_URL"; then
    echo "No se pudo descargar top-1m.csv de $TRANCO_URL" >&2
    exit 1
  fi
  if ! python3 -c 'import sys, zipfile; zipfile.ZipFile(sys.argv[1]).extract("top-1m.csv", sys.argv[2])' \
      "$work/top-1m.csv.zip" "$work" 2>/dev/null; then
    echo "top-1m.csv no es válido: lo descargado no es un zip con top-1m.csv" >&2
    exit 1
  fi
  if ! head -n 1 "$work/top-1m.csv" | grep -Eq '^[0-9]+,[^,]+$'; then
    echo "top-1m.csv no es válido: el formato esperado es posicion,dominio" >&2
    exit 1
  fi
  mv "$work/top-1m.csv" "$CSV_FILE"
  echo "top-1m.csv descargado ($(wc -l < "$CSV_FILE") filas)."
fi
