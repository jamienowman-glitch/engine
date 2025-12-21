from __future__ import annotations
import hashlib
import json
from typing import List, Optional, Literal, Tuple, Dict
from pydantic import BaseModel, Field, validator
import uuid

def _uuid() -> str:
    return uuid.uuid4().hex

class VectorStyle(BaseModel):
    fill_color: Optional[str] = None  # Hex
    stroke_color: Optional[str] = None  # Hex
    stroke_width: float = 1.0
    opacity: float = 1.0
    gradient: Optional[str] = None  # stub for future gradient support

    @validator("stroke_width")
    def stroke_width_non_negative(cls, value):
        if value < 0:
            raise ValueError("Stroke width cannot be negative")
        return value

    @validator("opacity")
    def opacity_in_range(cls, value):
        if not 0.0 <= value <= 1.0:
            raise ValueError("Opacity must be between 0 and 1")
        return value

class VectorTransform(BaseModel):
    x: float = 0.0
    y: float = 0.0
    scale_x: float = 1.0
    scale_y: float = 1.0
    rotation: float = 0.0  # degrees

    def matrix(self) -> Tuple[float, float, float, float, float, float]:
        import math

        theta = math.radians(self.rotation)
        cos_t = math.cos(theta)
        sin_t = math.sin(theta)
        a = cos_t * self.scale_x
        b = sin_t * self.scale_x
        c = -sin_t * self.scale_y
        d = cos_t * self.scale_y
        tx = self.x
        ty = self.y
        return (a, b, c, d, tx, ty)

class VectorNode(BaseModel):
    id: str = Field(default_factory=_uuid)
    type: str # "group", "rect", "circle", "path"
    transform: VectorTransform = Field(default_factory=VectorTransform)
    style: VectorStyle = Field(default_factory=VectorStyle)
    
class GroupNode(VectorNode):
    type: Literal["group"] = "group"
    children: List[VectorNode] = Field(default_factory=list)

class RectNode(VectorNode):
    type: Literal["rect"] = "rect"
    width: float = 100
    height: float = 100

class CircleNode(VectorNode):
    type: Literal["circle"] = "circle"
    radius: float = 50

class PathNode(VectorNode):
    type: Literal["path"] = "path"
    points: List[Tuple[float, float]] = Field(default_factory=list)
    closed: bool = False

class BooleanOperation(BaseModel):
    operation: Literal["union", "subtract", "intersect"]
    operands: List[str] = Field(default_factory=list)
    result_id: Optional[str] = None

class VectorScene(BaseModel):
    id: str = Field(default_factory=_uuid)
    tenant_id: str
    env: str
    width: float = 1920
    height: float = 1080
    root: GroupNode = Field(default_factory=GroupNode)
    boolean_ops: List[BooleanOperation] = Field(default_factory=list)
    meta: Dict[str, str] = Field(default_factory=dict)

    def layout_payload(self) -> Dict[str, object]:
        def node_payload(node: VectorNode) -> Dict[str, object]:
            base = {
                "id": node.id,
                "type": node.type,
                "transform": node.transform.model_dump(),
                "style": node.style.model_dump(),
            }
            if isinstance(node, GroupNode):
                base["children"] = [node_payload(child) for child in node.children]
            if isinstance(node, RectNode):
                base["width"] = node.width
                base["height"] = node.height
            if isinstance(node, CircleNode):
                base["radius"] = node.radius
            if isinstance(node, PathNode):
                base["points"] = node.points
                base["closed"] = node.closed
            return base

        payload = {
            "tenant": self.tenant_id,
            "env": self.env,
            "width": self.width,
            "height": self.height,
            "root": node_payload(self.root),
            "boolean_ops": [op.model_dump() for op in self.boolean_ops],
        }
        return payload

    def compute_layout_hash(self) -> str:
        payload = self.layout_payload()
        serialized = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
