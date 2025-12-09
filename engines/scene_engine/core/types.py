"""Core types for Scene Engine v1 (SE-01.A).

Neutral grid/box/scene definitions used by both service and recipe layers.
"""
from __future__ import annotations

import uuid
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class Recipe(str, Enum):
    wall = "wall"
    vector_explorer = "vector_explorer"
    vector_space_explorer = "vector_space_explorer"


class Grid(BaseModel):
    cols: int = Field(..., gt=0)
    rows: int = Field(1, gt=0)
    col_width: float = Field(1.0, gt=0)
    row_height: float = Field(1.0, gt=0)


class Box(BaseModel):
    id: str
    x: float
    y: float
    z: float = 0.0
    w: float = Field(..., ge=0)
    h: float = Field(..., ge=0)
    d: float = Field(1.0, ge=0)
    kind: str
    meta: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("x", "y", "z", "w", "h", "d", mode="before")
    def _coerce_numeric(cls, value: Any) -> float:
        if isinstance(value, (int, float)):
            return float(value)
        raise TypeError("Coordinates and dimensions must be numbers")


class GridBox3D(BaseModel):
    x: float
    y: float
    z: float
    w: float
    h: float
    d: float


class WorldPosition(BaseModel):
    x: float
    y: float
    z: float


class SceneNode(BaseModel):
    id: str
    kind: str
    gridBox3D: GridBox3D
    worldPosition: WorldPosition
    meta: Dict[str, Any] = Field(default_factory=dict)


class Camera(BaseModel):
    position: List[float] = Field(default_factory=lambda: [0.0, 5.0, 20.0])
    target: List[float] = Field(default_factory=lambda: [0.0, 5.0, 0.0])
    mode: str = "perspective"


class Scene(BaseModel):
    sceneId: str = Field(default_factory=lambda: uuid.uuid4().hex)
    nodes: List[SceneNode] = Field(default_factory=list)
    camera: Camera = Field(default_factory=Camera)


class SceneBuildRequest(BaseModel):
    grid: Grid
    boxes: List[Box]
    recipe: Recipe

    @field_validator("boxes")
    def _boxes_not_empty(cls, value: List[Box]) -> List[Box]:
        if not value:
            raise ValueError("boxes must not be empty")
        return value


class SceneBuildResult(BaseModel):
    scene: Scene


__all__ = [
    "Recipe",
    "Grid",
    "Box",
    "GridBox3D",
    "WorldPosition",
    "SceneNode",
    "Camera",
    "Scene",
    "SceneBuildRequest",
    "SceneBuildResult",
]
