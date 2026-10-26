# Autor: David Vaquero <pepesan@gmail.com>
# Licencia: GPL-3.0-only
# Build desde la raíz del repo: docker build -f dashboard/Dockerfile .
# (el dashboard depende del paquete webtechstats del directorio padre)

# --- 1. frontend Vue ---
FROM node:26.12.1-alpine AS frontend
WORKDIR /build
COPY dashboard/frontend/package.json dashboard/frontend/package-lock.json ./
RUN npm ci
COPY dashboard/frontend/ ./
RUN npm run build

# --- 2. runtime Python ---
FROM python:3.14.9-slim
COPY --from=ghcr.io/astral-sh/uv:0.13.5 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never PYTHONUNBUFFERED=1
WORKDIR /app

# Paquete webtechstats (raíz) y dashboard, respetando la ruta relativa `..` de uv.sources
COPY pyproject.toml ./pyproject.toml
COPY src ./src
COPY dashboard/pyproject.toml dashboard/uv.lock dashboard/.python-version ./dashboard/
COPY dashboard/src ./dashboard/src
WORKDIR /app/dashboard
RUN uv sync --frozen --no-dev

COPY --from=frontend /build/dist /app/frontend-dist
ENV WTS_FRONTEND_DIST=/app/frontend-dist PATH="/app/dashboard/.venv/bin:$PATH"

RUN useradd --system --no-create-home app
USER app
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --retries=5 \
  CMD python -c "import urllib.request as u; u.urlopen('http://127.0.0.1:8000/api/topics', timeout=3)"
CMD ["wts-dashboard", "--host", "0.0.0.0", "--port", "8000"]
