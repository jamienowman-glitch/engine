"""Sketch and Dimensional Constraint Models."""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field

from engines.scene_engine.core.geometry import Vector3, Transform, EulerAngles


# --- Entities ---

class SketchEntityKind(str, Enum):
    POINT = "point"
    LINE = "line"
    ARC = "arc"


class SketchPoint(BaseModel):
    id: str
    x: float
    y: float
    # Z is implicitly 0 in sketch plane


class SketchLine(BaseModel):
    id: str
    start_point_id: str
    end_point_id: str


class SketchArc(BaseModel):
    id: str
    center_point_id: str
    start_point_id: str
    end_point_id: str
    radius: float # Can be derived if valid, but constraint solver might need explicit or variable
    # direction? CW/CCW? 
    # For P0, simple 3-point definition or Center+Radius+Angles? 
    # Start/End points implies radius = dist(center, start) = dist(center, end).


class Sketch(BaseModel):
    id: str
    name: Optional[str] = None
    
    # Entities
    points: List[SketchPoint] = Field(default_factory=list)
    lines: List[SketchLine] = Field(default_factory=list)
    arcs: List[SketchArc] = Field(default_factory=list)
    
    # Constraints
    constraints: List['SketchConstraint'] = Field(default_factory=list)
    
    # Placement in 3D
    plane_transform: Transform = Field(
        default_factory=lambda: Transform(
            position=Vector3(x=0,y=0,z=0), 
            rotation=EulerAngles(x=0,y=0,z=0), 
            scale=Vector3(x=1,y=1,z=1)
        )
    )
    
    meta: Dict[str, Any] = Field(default_factory=dict)


# --- Constraints ---

class SketchConstraintKind(str, Enum):
    COINCIDENT = "coincident" # Point A = Point B
    DISTANCE = "distance"     # Distance(P1, P2) = d
    HORIZONTAL = "horizontal" # Line P1-P2 dy=0
    VERTICAL = "vertical"     # Line P1-P2 dx=0
    PARALLEL = "parallel"     # Line A // Line B
    PERPENDICULAR = "perpendicular" # Line A _|_ Line B
    EQUAL_LENGTH = "equal_length" # Length(Line A) = Length(Line B)


class SketchConstraint(BaseModel):
    id: str
    kind: SketchConstraintKind
    
    # Target Entities (depend on kind)
    entity_ids: List[str] 
    
    # Parameters
    value: Optional[float] = None # e.g. distance amount
    
    meta: Dict[str, Any] = Field(default_factory=dict)

# Rebuild models for recursive type (if needed for Pydantic v1/v2 compat, usually fine with string forward ref in list)
Sketch.update_forward_refs()
