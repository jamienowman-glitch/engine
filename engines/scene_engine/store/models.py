"""Persistence models for Scene Store (Level B)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from engines.scene_engine.core.scene_v2 import SceneV2


class SaveSceneRequest(BaseModel):
    scene: SceneV2
    name: Optional[str] = None
    tags: Optional[List[str]] = None
    meta: Dict[str, Any] = Field(default_factory=dict)


class SaveSceneResult(BaseModel):
    scene_id: str


class LoadSceneRequest(BaseModel):
    scene_id: str


class LoadSceneResult(BaseModel):
    scene: SceneV2
