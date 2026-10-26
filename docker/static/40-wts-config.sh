#!/bin/sh
# Genera config.json (flag de fuente de datos del frontend) a partir de WTS_SOURCE.
# Solo se aceptan valores conocidos: cualquier otra cosa cae en "reports" (informes estáticos).
set -eu
dir="${WTS_HTML_DIR:-/usr/share/nginx/html}"
case "${WTS_SOURCE:-reports}" in
    api) source=api ;;
    *) source=reports ;;
esac
printf '{"source":"%s"}\n' "$source" > "$dir/config.json"
