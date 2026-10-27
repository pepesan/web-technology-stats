#!/usr/bin/env bash
# Autor: David Vaquero <pepesan@gmail.com>
# Licencia: GPL-3.0-only
# Arranca MongoDB si ya fue inicializado (directorio de datos existente: ./data/mongodb o MONGO_DATA_DIR).
# Usar 00_init.sh en el primer arranque.
#
# Si hay copias de seguridad en BACKUP_DIR (webstats_*.archive.gz, ver PLAN.md) y la base está VACÍA, carga la más
# reciente tras arrancar (la restauración nunca borra nada: sin --drop; si la base ya tiene datos no se toca).
# Con backup, el arranque también funciona aunque el directorio de datos se haya perdido: se crea y se restaura.
#   MONGO_DATA_DIR  directorio de datos de MongoDB (por defecto ./data/mongodb)
#   BACKUP_DIR      carpeta de las copias de seguridad (por defecto ./data/backups, ignorada por git)
#   SKIP_RESTORE    =1 no carga ningún backup
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

DATA_DIR="${MONGO_DATA_DIR:-./data/mongodb}"
BACKUP_DIR="${BACKUP_DIR:-./data/backups}"
CONTAINER=webtechstats-mongodb

# Backup más reciente (los nombres llevan la fecha, así que el orden alfabético es el cronológico).
BACKUP=""
if [ "${SKIP_RESTORE:-0}" != 1 ]; then
  shopt -s nullglob
  backups=("$BACKUP_DIR"/*.archive.gz)
  shopt -u nullglob
  if [ "${#backups[@]}" -gt 0 ]; then
    BACKUP="${backups[${#backups[@]}-1]}"
  fi
fi

if [ ! -d "$DATA_DIR" ]; then
  if [ -z "$BACKUP" ]; then
    echo "No existe $DATA_DIR todavía. Ejecuta primero ./00_init.sh" >&2
    exit 1
  fi
  echo "No existe $DATA_DIR: se crea y se cargará el backup $BACKUP"
  mkdir -p "$DATA_DIR"
fi

docker compose up -d

if [ -n "$BACKUP" ]; then
  echo "Esperando a que MongoDB esté listo (healthcheck)..."
  ready=0
  for _ in $(seq 1 60); do
    status=$(docker inspect -f '{{.State.Health.Status}}' "$CONTAINER" 2>/dev/null || echo "starting")
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

  # Las credenciales salen de las variables del propio contenedor.
  count=$(docker exec "$CONTAINER" sh -c 'mongosh --quiet -u "$MONGO_INITDB_ROOT_USERNAME" -p "$MONGO_INITDB_ROOT_PASSWORD" --authenticationDatabase admin "$MONGO_INITDB_DATABASE" --eval "db.site.estimatedDocumentCount()"' 2>/dev/null | tail -n 1)
  if ! [[ "$count" =~ ^[0-9]+$ ]]; then
    echo "No se pudo contar los sitios de la base; no se carga el backup." >&2
    exit 1
  fi

  if [ "$count" -gt 0 ]; then
    echo "La base ya tiene $count sitios: no se carga el backup $BACKUP."
  else
    if [ -f "$BACKUP.sha256" ]; then
      # solo se compara el hash: el .sha256 puede llevar la ruta desde la que se generó (data/backups/...)
      expected=$(cut -d' ' -f1 "$BACKUP.sha256")
      actual=$(sha256sum "$BACKUP" | cut -d' ' -f1)
      if [ "$expected" != "$actual" ]; then
        echo "El backup $BACKUP no coincide con su sha256: no se carga." >&2
        exit 1
      fi
    else
      echo "Aviso: $BACKUP no tiene .sha256; se carga sin comprobar su integridad." >&2
    fi
    echo "Base vacía: cargando el backup $BACKUP (puede tardar unos minutos)..."
    docker exec -i "$CONTAINER" sh -c 'mongorestore -u "$MONGO_INITDB_ROOT_USERNAME" -p "$MONGO_INITDB_ROOT_PASSWORD" --authenticationDatabase admin --archive --gzip' < "$BACKUP"
    echo "Backup cargado."
  fi
fi

echo "MongoDB arrancado. Estado:"
docker compose ps
