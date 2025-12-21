"""Tests for Avatar Asset Kit (P13)."""

from engines.scene_engine.assets.service import create_package, load_package
from engines.scene_engine.assets.models import AvatarAssetManifest, AvatarAssetType
from engines.scene_engine.avatar.service import build_default_avatar

def test_asset_package_roundtrip():
    # 1. Create Scene
    scene, rig = build_default_avatar()
    original_node_count = len(scene.nodes)
    
    # 2. Create Package
    manifest = AvatarAssetManifest(
        name="Test Avatar",
        asset_type=AvatarAssetType.FULL_AVATAR,
        version="0.0.1"
    )
    
    package = create_package(scene, rig, manifest)
    
    assert package.manifest.name == "Test Avatar"
    assert len(package.nodes) == original_node_count
    assert len(package.meshes) > 0
    assert package.rig_definition is not None
    
    # 3. Load Package
    loaded_scene, loaded_rig = load_package(package)
    
    assert len(loaded_scene.nodes) == original_node_count
    assert len(loaded_scene.meshes) == len(scene.meshes)
    assert loaded_rig.root_bone_id == rig.root_bone_id
    
    # Verify deep copy (modifying loaded doesn't affect original)
    loaded_scene.nodes[0].id = "modified_id"
    assert scene.nodes[0].id != "modified_id"
