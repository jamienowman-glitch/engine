"""Avatar Asset Kit Service (P13)."""
from __future__ import annotations

import copy
from typing import Optional, List

from engines.scene_engine.core.scene_v2 import SceneV2, SceneNodeV2
from engines.scene_engine.avatar.models import AvatarRigDefinition
from engines.scene_engine.assets.models import AvatarAssetPackage, AvatarAssetManifest, AvatarAssetType

def create_package(
    scene: SceneV2,
    rig: Optional[AvatarRigDefinition] = None,
    manifest: Optional[AvatarAssetManifest] = None
) -> AvatarAssetPackage:
    """Creates a portable asset package from a Scene."""
    
    if not manifest:
        manifest = AvatarAssetManifest(
            name="Untitled Asset",
            asset_type=AvatarAssetType.FULL_AVATAR if rig else AvatarAssetType.PROP
        )
        
    # Deep copy components to ensure package is standalone
    # In a real engine, we'd filter unused meshes/materials.
    # Here we assume the scene is scoped to the asset.
    
    return AvatarAssetPackage(
        manifest=manifest,
        nodes=copy.deepcopy(scene.nodes),
        meshes=copy.deepcopy(scene.meshes),
        materials=copy.deepcopy(scene.materials),
        rig_definition=copy.deepcopy(rig) if rig else None
    )

import uuid

def load_package(package: AvatarAssetPackage) -> tuple[SceneV2, Optional[AvatarRigDefinition]]:
    """Loads a package into a new SceneV2 object."""
    
    scene = SceneV2(id=str(uuid.uuid4()))
    scene.nodes = copy.deepcopy(package.nodes)
    scene.meshes = copy.deepcopy(package.meshes)
    scene.materials = copy.deepcopy(package.materials)
    
    # Also load rig
    rig = copy.deepcopy(package.rig_definition)
    
    return scene, rig
