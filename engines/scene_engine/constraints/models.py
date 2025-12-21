"""Constraint Engine Models."""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional, List

from pydantic import BaseModel, Field

from engines.scene_engine.core.geometry import Vector3


class ConstraintKind(str, Enum):
    ANCHOR_TO_NODE = "anchor_to_node"
    ANCHOR_TO_WORLD = "anchor_to_world"
    KEEP_ON_PLANE = "keep_on_plane"
    MAINTAIN_DISTANCE = "maintain_distance"
    AIM_AT_NODE = "aim_at_node"
    ALIGN_AXIS = "align_axis"


class SceneConstraint(BaseModel):
    id: str
    kind: ConstraintKind
    node_id: str
    target_node_id: Optional[str] = None

    # Parameters
    plane_normal: Optional[Vector3] = None      # KEEP_ON_PLANE
    plane_offset: Optional[float] = None
    
    distance: Optional[float] = None            # MAINTAIN_DISTANCE
    
    source_axis: Optional[Vector3] = None       # ALIGN_AXIS / AIM_AT_NODE (forward axis)
    target_axis: Optional[Vector3] = None       # ALIGN_AXIS
    
    world_target: Optional[Vector3] = None      # ANCHOR_TO_WORLD target or AIM world target
    
    weight: float = 1.0

    meta: Dict[str, Any] = Field(default_factory=dict)
