"""Service-layer schemas for Scene Engine HTTP surface."""
from __future__ import annotations

from pydantic import BaseModel

from engines.scene_engine.core.types import SceneBuildRequest, SceneBuildResult


class SceneBuildResponse(BaseModel):
    scene: SceneBuildResult

    class Config:
        arbitrary_types_allowed = True
