"""HTTP routes for Scene Engine service (SE-01.B)."""
from __future__ import annotations

from fastapi import APIRouter

from engines.scene_engine.core.mapping import map_boxes
from engines.scene_engine.core.types import Scene, SceneBuildRequest, SceneBuildResult

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.post("/scene/build", response_model=SceneBuildResult)
def build_scene(request: SceneBuildRequest) -> SceneBuildResult:
    nodes = map_boxes(request.grid, request.boxes, request.recipe)
    scene = Scene(nodes=nodes)
    return SceneBuildResult(scene=scene)
