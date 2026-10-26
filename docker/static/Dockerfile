# Imagen estática del dashboard: frontend Vue compilado + informes JSON servidos por nginx.
# Sin servidor de aplicación ni base de datos. Build desde la raíz del repo (con ./reports ya generado):
#   ./60_build_static_image.sh [TAG] [--push]

# --- 1. frontend Vue ---
FROM node:26.12.1-alpine AS frontend
WORKDIR /build
COPY dashboard/frontend/package.json dashboard/frontend/package-lock.json ./
RUN npm ci
COPY dashboard/frontend/ ./
RUN npm run build

# --- 2. nginx ---
FROM nginx:1.31.8-alpine
COPY docker/static/nginx.conf /etc/nginx/conf.d/default.conf
COPY docker/static/40-wts-config.sh /docker-entrypoint.d/40-wts-config.sh
RUN chmod +x /docker-entrypoint.d/40-wts-config.sh
COPY --from=frontend /build/dist /usr/share/nginx/html
COPY reports /usr/share/nginx/html/reports
ENV WTS_SOURCE=reports
EXPOSE 80
HEALTHCHECK --interval=15s --timeout=5s --retries=5 \
  CMD wget -q -O /dev/null http://127.0.0.1/reports/index.json || exit 1
