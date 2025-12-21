"""Tests for Turntable Engine (P9)."""

import math
from engines.scene_engine.extras.turntable import TurntableRequest, generate_turntable_sequence
from engines.scene_engine.core.scene_v2 import SceneV2
from engines.scene_engine.core.geometry import Vector3
from engines.scene_engine.camera.models import Camera

def test_turntable_rotation():
    scene = SceneV2(id="s1")
    # Add dummy cam at +Z
    scene.camera = Camera(
        id="c1",
        position=Vector3(x=0, y=0, z=5),
        target=Vector3(x=0,y=0,z=0),
        fov_deg=50
    )
    
    req = TurntableRequest(num_frames=4, rotations=1.0)
    frames = generate_turntable_sequence(scene, req)
    
    assert len(frames) == 4
    
    # Frame 0: 0 degrees (start) -> (0,0,5)
    # Frame 1: 90 degrees -> x should be sin(90)*5 = 5, z = cos(90)*5 = 0
    # Implementation uses sin/cos logic. 
    # start_azimuth = atan2(0, 5) = 0.
    # Frame 1: azimuth = pi/2.
    # x = 0 + 5 * 1 = 5. z = 0 + 5 * 0 = 0.
    
    f1_cam = frames[1].camera
    assert abs(f1_cam.position.x - 5.0) < 0.01
    assert abs(f1_cam.position.z) < 0.01
    
    # Frame 2: 180 degrees -> (0, 0, -5)
    f2_cam = frames[2].camera
    assert abs(f2_cam.position.z + 5.0) < 0.01

