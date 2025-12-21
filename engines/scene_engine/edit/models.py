"""Command and Result models for Scene Edit Engine (Level B)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from engines.scene_engine.core.geometry import Material, PrimitiveParams, Transform
from engines.scene_engine.core.scene_v2 import AttachmentPoint, SceneV2


class CreateSceneCommand(BaseModel):
    name: Optional[str] = None
    tags: Optional[List[str]] = None
    meta: Dict[str, Any] = Field(default_factory=dict)
    seed_from_scene: Optional[SceneV2] = None


class CreateSceneResult(BaseModel):
    scene: SceneV2


class AddPrimitiveNodeCommand(BaseModel):
    scene: SceneV2
    primitive: PrimitiveParams
    transform: Transform
    material: Optional[Material] = None
    parent_node_id: Optional[str] = None
    meta: Dict[str, Any] = Field(default_factory=dict)


class AddPrimitiveNodeResult(BaseModel):
    scene: SceneV2
    node_id: str


class UpdateNodeTransformCommand(BaseModel):
    scene: SceneV2
    node_id: str
    transform: Transform


class UpdateNodeTransformResult(BaseModel):
    scene: SceneV2


class UpdateNodeMetaCommand(BaseModel):
    scene: SceneV2
    node_id: str
    meta: Dict[str, Any]


class UpdateNodeMetaResult(BaseModel):
    scene: SceneV2


class SetNodeAttachmentsCommand(BaseModel):
    scene: SceneV2
    node_id: str
    attachments: List[AttachmentPoint]


class SetNodeAttachmentsResult(BaseModel):
    scene: SceneV2


class DeleteNodeCommand(BaseModel):
    scene: SceneV2
    node_id: str


class DeleteNodeResult(BaseModel):
    scene: SceneV2
