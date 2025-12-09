"""FastAPI app for BBK local pipeline service."""
from __future__ import annotations

import importlib.util
from pathlib import Path

from fastapi import FastAPI


def _load_routes():
    routes_path = Path(__file__).resolve().parent / "routes.py"
    spec = importlib.util.spec_from_file_location("bbk_routes", routes_path)
    module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    assert spec and spec.loader
    spec.loader.exec_module(module)  # type: ignore[attr-defined]
    return module.router  # type: ignore[attr-defined]


def create_app() -> FastAPI:
    app = FastAPI(title="BBK Service", version="0.1.0")
    app.include_router(_load_routes())
    return app


app = create_app()
