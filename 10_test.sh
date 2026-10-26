#!/usr/bin/env bash
# Ejecuta la batería de tests del CLI y del motor de detección.
# No requiere MongoDB real (usa mongomock) ni red (usa fixtures HTML locales).
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

uv run pytest tests/ -v "$@"
