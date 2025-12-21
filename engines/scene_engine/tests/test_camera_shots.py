"""Tests for Camera Shot Language (P7)."""

import math
from engines.scene_engine.camera.shots import ShotRequest, ShotSize, ShotAngle, apply_shot
from engines.scene_engine.avatar.service import build_default_avatar
from engines.scene_engine.core.geometry import Vector3

def test_shot_close_up_position():
    scene, rig = build_default_avatar()
    
    req = ShotRequest(size=ShotSize.CLOSE_UP, angle=ShotAngle.FRONT)
    final_scene = apply_shot(scene, rig, req)
    
    assert final_scene.camera is not None
    cam = final_scene.camera
    
    # Verify Camera is close to target
    # Distance approx 0.8
    dist = math.sqrt(
        (cam.position.x - cam.target.x)**2 +
        (cam.position.y - cam.target.y)**2 +
        (cam.position.z - cam.target.z)**2
    )
    assert 0.7 < dist < 0.9

def test_shot_side_profile():
    scene, rig = build_default_avatar()
    
    req = ShotRequest(size=ShotSize.MEDIUM_SHOT, angle=ShotAngle.SIDE_PROFILE_LEFT)
    final_scene = apply_shot(scene, rig, req)
    
    cam = final_scene.camera
    # Left profile: Camera should be at -X (approx) relative to target
    # calculated: x = dist * sin(-90) = -dist
    # z = dist * cos(-90) = 0
    
    dx = cam.position.x - cam.target.x
    dz = cam.position.z - cam.target.z
    
    # Expect dx negative, dz near 0
    assert dx < -1.0
    assert abs(dz) < 0.1
