"""Camera and Lighting Models (Level B)."""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from engines.scene_engine.core.geometry import Vector3


class CameraProjection(str, Enum):
    PERSPECTIVE = "perspective"
    ORTHOGRAPHIC = "orthographic"


class CameraShotKind(str, Enum):
    HERO_CLOSEUP = "hero_closeup"
    FULL_BODY = "full_body"
    WIDE_ENVIRONMENT = "wide_environment"


class Camera(BaseModel):
    id: str
    name: Optional[str] = None
    projection: CameraProjection = CameraProjection.PERSPECTIVE
    fov_deg: float = 50.0
    near: float = 0.1
    far: float = 1000.0
    position: Vector3
    target: Vector3
    up: Vector3 = Vector3(x=0.0, y=1.0, z=0.0)
    meta: Dict[str, Any] = Field(default_factory=dict)


class LightKind(str, Enum):
    DIRECTIONAL = "directional"
    POINT = "point"
    SPOT = "spot"


class Light(BaseModel):
    id: str
    name: Optional[str] = None
    kind: LightKind = LightKind.DIRECTIONAL
    color: Vector3 = Vector3(x=1.0, y=1.0, z=1.0)
    intensity: float = 1.0
    position: Optional[Vector3] = None
    direction: Optional[Vector3] = None
    range: Optional[float] = None
    angle_deg: Optional[float] = None
    meta: Dict[str, Any] = Field(default_factory=dict)


class CameraRig(BaseModel):
    camera: Camera
    lights: List[Light] = Field(default_factory=list)
    meta: Dict[str, Any] = Field(default_factory=dict)
