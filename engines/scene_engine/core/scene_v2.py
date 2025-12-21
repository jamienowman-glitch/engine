"""Scene Graph V2 models (Level B)."""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from engines.scene_engine.core.geometry import Material, Mesh, Transform
from engines.scene_engine.camera.models import Camera, Light
from engines.scene_engine.constraints.models import SceneConstraint
from engines.scene_engine.core.types import SceneBuildRequest


class AttachmentPoint(BaseModel):
    name: str
    local_transform: Transform


class SceneNodeV2(BaseModel):
    id: str
    name: Optional[str] = None
    transform: Transform
    mesh_id: Optional[str] = None
    material_id: Optional[str] = None
    children: List[SceneNodeV2] = Field(default_factory=list)
    attachments: List[AttachmentPoint] = Field(default_factory=list)
    meta: Dict[str, Any] = Field(default_factory=dict)


class ConstructionOpKind(str, Enum):
    CREATE_PRIMITIVE = "CREATE_PRIMITIVE"
    BOOLEAN_UNION = "BOOLEAN_UNION"
    BOOLEAN_SUBTRACT = "BOOLEAN_SUBTRACT"
    BOOLEAN_INTERSECT = "BOOLEAN_INTERSECT"
    APPLY_TRANSFORM = "APPLY_TRANSFORM"
    APPLY_MODIFIER = "APPLY_MODIFIER"


class ConstructionOp(BaseModel):
    id: str
    kind: ConstructionOpKind
    inputs: List[str] = Field(default_factory=list)
    params: Dict[str, Any] = Field(default_factory=dict)
    result_node_id: Optional[str] = None


class SceneV2(BaseModel):
    id: str
    nodes: List[SceneNodeV2] = Field(default_factory=list)
    meshes: List[Mesh] = Field(default_factory=list)
    materials: List[Material] = Field(default_factory=list)
    camera: Optional[Camera] = None
    lights: List[Light] = Field(default_factory=list)
    constraints: List[SceneConstraint] = Field(default_factory=list)
    environment: Optional[Dict[str, Any]] = None
    history: Optional[List[ConstructionOp]] = None
    meta: Dict[str, Any] = Field(default_factory=dict)


class SceneGraphBuildRequest(BaseModel):
    v1_request: SceneBuildRequest


class SceneGraphBuildResult(BaseModel):
    scene: SceneV2


# Resolve forward references for recursive SceneNodeV2
SceneNodeV2.model_rebuild()
SceneV2.model_rebuild()

