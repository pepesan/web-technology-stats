#!/usr/bin/env bash
# Autor: David Vaquero <pepesan@gmail.com>
# Licencia: GPL-3.0-only
# Aplica (o revierte) host/90-webtechstats.conf, ajustes del kernel para muchas conexiones simultáneas.
#
#   ./host/aplicar_sysctl.sh --dry-run    muestra valor actual -> propuesto; no cambia nada ni pide root
#   sudo ./host/aplicar_sysctl.sh         guarda los valores actuales, instala el fichero y lo aplica
#   sudo ./host/aplicar_sysctl.sh --revert  restaura los valores guardados y elimina el fichero
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

CONF="90-webtechstats.conf"
TARGET="/etc/sysctl.d/90-webtechstats.conf"
BACKUP="/etc/sysctl.d/.90-webtechstats.previous"

# Lee "clave = valor" del fichero (ignora comentarios y líneas vacías).
proposed() { grep -E '^[a-z0-9_.]+ = ' "$CONF"; }
current() { sysctl -n "$1" 2>/dev/null | tr '\t' ' ' || echo "n/d"; }

show_diff() {
  printf '%-40s %-22s %s\n' "parámetro" "actual" "propuesto"
  while IFS=' = ' read -r key _ value; do
    key="${key%% *}"
    value="$(proposed | grep -E "^${key//./\\.} = " | sed 's/^[^=]*= //')"
    printf '%-40s %-22s %s\n' "$key" "$(current "$key")" "$value"
  done < <(proposed | sed 's/ = / = /')
}

case "${1:-}" in
  --dry-run)
    show_diff
    echo
    echo "Dry-run: no se ha modificado nada."
    exit 0
    ;;
  --revert)
    [ "$(id -u)" -eq 0 ] || { echo "Necesita root: sudo $0 --revert" >&2; exit 1; }
    if [ -f "$BACKUP" ]; then
      sysctl -p "$BACKUP" >/dev/null
      rm -f "$BACKUP"
      echo "Valores anteriores restaurados."
    else
      echo "No hay copia de los valores anteriores ($BACKUP); solo se elimina el fichero." >&2
    fi
    rm -f "$TARGET"
    echo "Eliminado $TARGET."
    exit 0
    ;;
  "")
    [ "$(id -u)" -eq 0 ] || { echo "Necesita root: sudo $0   (o usa --dry-run para ver el cambio)" >&2; exit 1; }
    ;;
  *)
    echo "Uso: $0 [--dry-run | --revert]" >&2
    exit 2
    ;;
esac

show_diff
# Copia de los valores actuales, para poder revertir (solo la primera vez).
if [ ! -f "$BACKUP" ]; then
  while read -r key _; do
    echo "$key = $(current "$key")"
  done < <(proposed) > "$BACKUP"
  echo "Valores anteriores guardados en $BACKUP"
fi
install -m 0644 "$CONF" "$TARGET"
sysctl -p "$TARGET"
echo "Aplicado. Persistirá tras reiniciar. Para revertir: sudo $0 --revert"
