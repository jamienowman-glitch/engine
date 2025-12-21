"""Tests for Camera Engine."""
import pytest
from engines.scene_engine.core.scene_v2 import SceneV2, SceneNodeV2
from engines.scene_engine.core.geometry import Transform, Vector3, EulerAngles, Quaternion
from engines.scene_engine.camera.service import (
    create_orbit_camera_rig_for_node,
    attach_camera_rig_to_scene,
    create_avatar_hero_shot,
)
from engines.scene_engine.camera.models import CameraShotKind, CameraProjection

def test_create_orbit_camera_rig_for_node_basic():
    # Setup Scene with 1 node at (10, 0, 10)
    node = SceneNodeV2(
        id="target_node",
        transform=Transform(
            position=Vector3(x=10, y=0, z=10),
            rotation=Quaternion(x=0, y=0, z=0, w=1),
            scale=Vector3(x=1, y=1, z=1)
        )
    )
    scene = SceneV2(id="test", nodes=[node])
    
    # Create Rig
    rig = create_orbit_camera_rig_for_node(
        scene, "target_node", 
        distance=5.0, 
        height=2.0, 
        shot_kind=CameraShotKind.FULL_BODY
    )
    
    # Assert
    cam = rig.camera
    # Target should be node position (10, 0, 10)
    assert cam.target.x == 10
    assert cam.target.z == 10
    
    # Position should be target + offset
    # We implemented z + distance.
    assert cam.position.x == 10
    assert cam.position.y == 2.0  # target.y + height (0 + 2)
    assert cam.position.z == 15.0 # target.z + distance (10 + 5)
    
    assert len(rig.lights) >= 2


def test_attach_camera_rig_to_scene():
    scene = SceneV2(id="test")
    assert scene.camera is None
    assert len(scene.lights) == 0
    
    rig = create_orbit_camera_rig_for_node(scene, "missing", 5, 2)
    # If node missing, fallback to 0,0,0
    
    updated = attach_camera_rig_to_scene(scene, rig)
    assert updated.camera is not None
    assert updated.camera.id == rig.camera.id
    assert len(updated.lights) == 2


def test_create_avatar_hero_shot():
    # Avatar root at origin
    node = SceneNodeV2(
        id="avatar_root",
        transform=Transform(
            position=Vector3(x=0, y=0, z=0),
            rotation=Quaternion(x=0, y=0, z=0, w=1),
            scale=Vector3(x=1, y=1, z=1)
        )
    )
    scene = SceneV2(id="test", nodes=[node])
    
    scene = create_avatar_hero_shot(scene, "avatar_root")
    
    assert scene.camera is not None
    # Check FOV for Hero Shot
    assert scene.camera.fov_deg == 35.0
    
    # Check Target Adjustment (we added +1.5 to Y)
    assert scene.camera.target.y == 1.5
    # Position height should also be adjusted (1.4 + 1.5 = 2.9)
    assert scene.camera.position.y == 2.9
