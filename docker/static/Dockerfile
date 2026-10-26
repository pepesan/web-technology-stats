# Autor: David Vaquero <pepesan@gmail.com>
# Licencia: GPL-3.0-only
# Imagen estática del dashboard: frontend Vue compilado + informes JSON servidos por nginx.
# Sin servidor de aplicación ni base de datos. Build desde la raíz del repo (con ./reports ya generado):
#   ./scripts/build_static_image.sh [TAG] [--push]

# --- 1. frontend Vue ---
FROM node:26.12.1-alpine AS frontend
WORKDIR /build
COPY dashboard/frontend/package.json dashboard/frontend/package-lock.json ./
RUN npm ci
COPY dashboard/frontend/ ./
RUN npm run build && echo '{"source":"reports"}' > dist/config.json

# --- 2. nginx sin privilegios (usuario 101, puerto 8080) ---
FROM nginxinc/nginx-unprivileged:1.31.7-alpine
LABEL org.opencontainers.image.licenses="GPL-3.0-only" \
      org.opencontainers.image.source="https://github.com/pepesan/web-technology-stats"
# Parches de seguridad del sistema base (Trivy) y vuelta a usuario sin privilegios al final.
USER root
RUN apk upgrade --no-cache
COPY docker/static/nginx.conf /etc/nginx/conf.d/default.conf
COPY --chmod=755 docker/static/40-wts-config.sh /docker-entrypoint.d/40-wts-config.sh
# config.json llega con dueño 101 para que el entrypoint (sin root) pueda reescribirlo según WTS_SOURCE.
COPY --from=frontend --chown=101:101 /build/dist /usr/share/nginx/html
COPY --chown=101:101 reports /usr/share/nginx/html/reports
ENV WTS_SOURCE=reports
USER 101
EXPOSE 8080
HEALTHCHECK --interval=15s --timeout=5s --retries=5 \
  CMD wget -q -O /dev/null http://127.0.0.1:8080/reports/index.json || exit 1
