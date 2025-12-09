"""Aggregate app for universal chat transports (PLAN-024)."""
from __future__ import annotations

from fastapi import FastAPI

from engines.chat.service.http_transport import app as http_app
from engines.chat.service.ws_transport import router as ws_router
from engines.chat.service.sse_transport import router as sse_router
from engines.media.service.routes import router as media_router
from engines.maybes.routes import router as maybes_router
from engines.nexus.vector_explorer.routes import router as vector_explorer_router
from engines.nexus.vector_explorer.ingest_routes import router as vector_ingest_router


def create_app() -> FastAPI:
    app = http_app
    app.include_router(ws_router)
    app.include_router(sse_router)
    app.include_router(media_router)
    app.include_router(maybes_router)
    app.include_router(vector_explorer_router)
    app.include_router(vector_ingest_router)
    return app


app = create_app()
