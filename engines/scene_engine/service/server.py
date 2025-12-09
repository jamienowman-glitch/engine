"""FastAPI application for Scene Engine (SE-01.B)."""
from __future__ import annotations

from fastapi import FastAPI

from engines.scene_engine.service.routes import router


def create_app() -> FastAPI:
    app = FastAPI(title="Scene Engine", version="0.1.0")
    app.include_router(router)
    return app


app = create_app()
