"""Avatar Asset Kit Models (P13)."""
from __future__ import annotations

from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from engines.scene_engine.core.scene_v2 import SceneNodeV2
from engines.scene_engine.core.geometry import Mesh, Material
from engines.scene_engine.avatar.models import AvatarRigDefinition

class AvatarAssetType(str, Enum):
    FULL_AVATAR = "full_avatar"
    OUTFIT = "outfit"
    POSE_PACK = "pose_pack"
    ENVIRONMENT = "environment"
    PROP = "prop"

class AvatarAssetManifest(BaseModel):
    name: str
    asset_type: AvatarAssetType
    author: Optional[str] = None
    version: str = "1.0.0"
    description: Optional[str] = None
    thumbnail_uri: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    meta: Dict[str, Any] = Field(default_factory=dict)

class AvatarAssetPackage(BaseModel):
    """A portable package containing all data needed to reconstruct the asset."""
    manifest: AvatarAssetManifest
    
    # Payload
    # For a full avatar, we need the rig, nodes, meshes, materials.
    # Note: Textures are usually referenced by URI. A 'Marketplace' package might ZIP them.
    # For this 'Shape' definition, we store the structure.
    
    nodes: List[SceneNodeV2] = Field(default_factory=list)
    meshes: List[Mesh] = Field(default_factory=list)
    materials: List[Material] = Field(default_factory=list)
    
    rig_definition: Optional[AvatarRigDefinition] = None
    
    # If Pose Pack
    # poses: List[PoseDefinition] = ... (P1 implementation needed PoseDefinition export)
