"""Curves and Surfaces Data Models (NURBS Core)."""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field

from engines.scene_engine.core.geometry import Vector3


class CurveKind(str, Enum):
    POLYLINE = "polyline"
    BEZIER = "bezier"
    NURBS = "nurbs"


class SplineNode(BaseModel):
    """Control Point often with Weight."""
    position: Vector3
    weight: float = 1.0


class PolylineData(BaseModel):
    points: List[Vector3]
    closed: bool = False


class BezierData(BaseModel):
    # Standard cubic bezier(s)? Or recursive?
    # Let's say generic order defined by list of points.
    points: List[Vector3]


class NurbsCurveData(BaseModel):
    degree: int
    knots: List[float]
    control_points: List[SplineNode]
    # In NURBS, #knots = #control_points + degree + 1


class Curve(BaseModel):
    id: str
    kind: CurveKind
    
    # One of
    polyline: Optional[PolylineData] = None
    bezier: Optional[BezierData] = None
    nurbs: Optional[NurbsCurveData] = None
    
    meta: Dict[str, Any] = Field(default_factory=dict)


# Surfaces

class NurbsSurfaceData(BaseModel):
    degree_u: int
    degree_v: int
    knots_u: List[float]
    knots_v: List[float]
    
    # Control Points Grid [u][v]
    # Flattened or 2D list? 2D list of SplineNode.
    control_points: List[List[SplineNode]]


class SurfaceKind(str, Enum):
    NURBS = "nurbs"
    PLANE = "plane" # Could be represented as simplified NURBS too


class Surface(BaseModel):
    id: str
    kind: SurfaceKind
    
    nurbs: Optional[NurbsSurfaceData] = None
    meta: Dict[str, Any] = Field(default_factory=dict)
