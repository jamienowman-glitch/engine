"""Data models for 3D View & Selection Engine."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from engines.scene_engine.core.geometry import Vector3
from engines.scene_engine.core.scene_v2 import SceneV2


class ViewportSpec(BaseModel):
    # Camera definition
    camera_node_id: Optional[str] = None
    camera_position: Optional[Vector3] = None
    camera_target: Optional[Vector3] = None
    up: Vector3 = Field(default_factory=lambda: Vector3(x=0, y=1, z=0))

    # Projection parameters
    fov_y_degrees: float = 45.0
    aspect_ratio: float = 1.33  # 4:3 default
    near: float = 0.1
    far: float = 1000.0

    # Screen parameters
    screen_width: int
    screen_height: int


class NodeViewInfo(BaseModel):
    node_id: str
    visible: bool
    # (min_x, min_y, max_x, max_y) in normalized screen space [0, 1]
    # Origin top-left? User said 0=left/top.
    screen_bbox: Optional[Tuple[float, float, float, float]] = None
    screen_area_fraction: Optional[float] = None
    average_depth: Optional[float] = None
    meta: Dict[str, Any] = Field(default_factory=dict)


class ViewAnalysisRequest(BaseModel):
    scene: SceneV2
    viewport: ViewportSpec


class ViewAnalysisResult(BaseModel):
    nodes: List[NodeViewInfo]
    meta: Dict[str, Any] = Field(default_factory=dict)


class PickNodeRequest(BaseModel):
    scene: SceneV2
    viewport: ViewportSpec
    screen_x: float  # [0, 1]
    screen_y: float  # [0, 1]


class PickNodeResult(BaseModel):
    node_id: Optional[str] = None
    hit_position: Optional[Vector3] = None
    hit_normal: Optional[Vector3] = None
    meta: Dict[str, Any] = Field(default_factory=dict)
