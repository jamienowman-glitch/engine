"""Core geometry types for Scene Engine V2 (Level B)."""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field


class Vector3(BaseModel):
    x: float
    y: float
    z: float

    def add(self, other: Vector3) -> Vector3:
        return Vector3(x=self.x + other.x, y=self.y + other.y, z=self.z + other.z)

    def sub(self, other: Vector3) -> Vector3:
        return Vector3(x=self.x - other.x, y=self.y - other.y, z=self.z - other.z)

    def mul(self, scalar: float) -> Vector3:
        return Vector3(x=self.x * scalar, y=self.y * scalar, z=self.z * scalar)

    def dot(self, other: Vector3) -> float:
        return self.x * other.x + self.y * other.y + self.z * other.z

    def cross(self, other: Vector3) -> Vector3:
        return Vector3(
            x=self.y * other.z - self.z * other.y,
            y=self.z * other.x - self.x * other.z,
            z=self.x * other.y - self.y * other.x
        )

    def magnitude(self) -> float:
        import math
        return math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z)

    def normalize(self) -> Vector3:
        m = self.magnitude()
        if m == 0:
            return Vector3(x=0, y=0, z=0)
        return self.mul(1.0 / m)


class UV(BaseModel):
    u: float
    v: float


class Quaternion(BaseModel):
    x: float
    y: float
    z: float
    w: float


class EulerAngles(BaseModel):
    x: float
    y: float
    z: float
    order: str = "XYZ"


class Transform(BaseModel):
    position: Vector3
    rotation: Union[Quaternion, EulerAngles]
    scale: Vector3


class PrimitiveKind(str, Enum):
    BOX = "BOX"
    SPHERE = "SPHERE"
    CYLINDER = "CYLINDER"
    CAPSULE = "CAPSULE"
    PLANE = "PLANE"


class BoxParams(BaseModel):
    kind: Literal[PrimitiveKind.BOX] = PrimitiveKind.BOX
    width: float
    height: float
    depth: float


class SphereParams(BaseModel):
    kind: Literal[PrimitiveKind.SPHERE] = PrimitiveKind.SPHERE
    radius: float
    widthSegments: int = 32
    heightSegments: int = 16


class CylinderParams(BaseModel):
    kind: Literal[PrimitiveKind.CYLINDER] = PrimitiveKind.CYLINDER
    radiusTop: float
    radiusBottom: float
    height: float
    radialSegments: int = 32


class CapsuleParams(BaseModel):
    kind: Literal[PrimitiveKind.CAPSULE] = PrimitiveKind.CAPSULE
    radius: float
    length: float
    capSegments: int = 4
    radialSegments: int = 8


class PlaneParams(BaseModel):
    kind: Literal[PrimitiveKind.PLANE] = PrimitiveKind.PLANE
    width: float
    height: float
    widthSegments: int = 1
    heightSegments: int = 1


PrimitiveParams = Union[
    BoxParams, SphereParams, CylinderParams, CapsuleParams, PlaneParams
]


class Material(BaseModel):
    id: str
    name: Optional[str] = None
    base_color: Optional[Vector3] = None
    metallic: Optional[float] = None
    roughness: Optional[float] = None
    emissive: Optional[Vector3] = None
    opacity: Optional[float] = None
    # keys are texture slots (e.g. "albedo", "normal"), values are asset IDs
    texture_slots: Dict[str, str] = Field(default_factory=dict)
    meta: Dict[str, Any] = Field(default_factory=dict)


class Mesh(BaseModel):
    id: str
    name: Optional[str] = None
    vertices: List[Vector3]
    normals: Optional[List[Vector3]] = None
    uvs: Optional[List[UV]] = None
    indices: List[int]
    bounds_min: Optional[Vector3] = None
    bounds_max: Optional[Vector3] = None
    primitive_source: Optional[PrimitiveParams] = None
