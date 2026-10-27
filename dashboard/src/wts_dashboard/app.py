# Autor: David Vaquero <pepesan@gmail.com>
# Licencia: GPL-3.0-only
"""Aplicación FastAPI: API JSON bajo /api + frontend Vue compilado (frontend/dist)."""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from webtechstats.config import MongoConfig
from webtechstats.db import close_db, init_db
from webtechstats.topics import TOPICS

from .service import DashboardService

TLD_PATTERN = r"^[a-z][a-z0-9-]{0,23}$"  # sin puntos ni espacios: se compara literalmente
SOURCE_PATTERN = r"^[a-z0-9_-]{1,40}$"  # nombre de listado (tag-sources): sin espacios ni símbolos

# WTS_FRONTEND_DIST permite ubicar el frontend compilado fuera del árbol del código (imagen Docker).
FRONTEND_DIST = Path(
    os.environ.get("WTS_FRONTEND_DIST") or Path(__file__).resolve().parents[2] / "frontend" / "dist"
)


def create_app(connect: bool = True, cache_ttl: float = 30.0, frontend_dist: Path | None = FRONTEND_DIST) -> FastAPI:
    """`connect=False` deja la conexión a MongoDB en manos del llamador (tests)."""

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        if connect:
            init_db(MongoConfig.load())
        yield
        if connect:
            close_db()

    app = FastAPI(title="web-technology-stats dashboard", lifespan=lifespan)
    service = DashboardService(cache_ttl=cache_ttl)

    @app.get("/config.json")
    def frontend_config() -> dict:
        # Flag de fuente de datos del frontend: aquí siempre la API en vivo.
        return {"source": "api"}

    @app.get("/api/batches")
    def batches() -> list[dict]:
        return service.batches()

    @app.get("/api/topics")
    def topics() -> dict[str, str]:
        return TOPICS

    @app.get("/api/overview")
    def overview(
        batch: int | None = None,
        max_position: int | None = Query(None, ge=1),
        tld: str | None = Query(None, pattern=TLD_PATTERN),
        source: str | None = Query(None, pattern=SOURCE_PATTERN),
    ) -> dict:
        return service.overview(batch, max_position, tld, source)

    @app.get("/api/topics/{topic}")
    def topic_ranking(
        topic: str,
        batch: int | None = None,
        limit: int = Query(15, ge=1, le=500),
        category: str | None = None,
        max_position: int | None = Query(None, ge=1),
        tld: str | None = Query(None, pattern=TLD_PATTERN),
        source: str | None = Query(None, pattern=SOURCE_PATTERN),
    ) -> dict:
        if topic not in TOPICS:
            raise HTTPException(status_code=404, detail=f"Tema desconocido: {topic}")
        return service.topic_ranking(
            topic, batch=batch, limit=limit, category=category, max_position=max_position, tld=tld, source=source
        )

    if frontend_dist is not None and (frontend_dist / "index.html").is_file():
        app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str) -> FileResponse:
            candidate = (frontend_dist / path).resolve()
            if path and candidate.is_file() and frontend_dist.resolve() in candidate.parents:
                return FileResponse(candidate)
            return FileResponse(frontend_dist / "index.html")

    return app
