"""Snapshot & Turntable Engine (P9)."""
from __future__ import annotations

import copy
import math
from typing import List

from pydantic import BaseModel

from engines.scene_engine.core.scene_v2 import SceneV2
from engines.scene_engine.core.geometry import Vector3
from engines.scene_engine.camera.service import create_orbit_camera_rig_for_node, attach_camera_rig_to_scene, CameraShotKind

class TurntableRequest(BaseModel):
    num_frames: int = 36
    duration_sec: float = 3.0 # Not used for frame gen, but metadata?
    rotations: float = 1.0 # 1 full spin
    
def generate_turntable_sequence(scene: SceneV2, request: TurntableRequest) -> List[SceneV2]:
    """Generates a sequence of scenes with the camera rotated around the target."""
    frames = []
    
    # 1. Base Camera State
    # We need a camera. If none, create default Hero shot for now?
    base_scene = scene
    if not base_scene.camera:
        # Auto-add camera
        # Find something to look at? Origin.
        rig = create_orbit_camera_rig_for_node(base_scene, "origin", distance=3.0, height=1.0)
        base_scene = attach_camera_rig_to_scene(base_scene, rig)
        
    cam = base_scene.camera
    target = cam.target
    current_pos = cam.position
    
    # Calculate radius & current angles
    dx = current_pos.x - target.x
    dy = current_pos.y - target.y
    dz = current_pos.z - target.z
    
    radius = math.sqrt(dx*dx + dz*dz)
    start_azimuth = math.atan2(dx, dz) # Z-forward (0,1)? coords are (x,z)
    
    for i in range(request.num_frames):
        fraction = i / float(request.num_frames)
        angle_delta = fraction * (2 * math.pi * request.rotations)
        
        azimuth = start_azimuth + angle_delta
        
        # New Pos
        nx = target.x + radius * math.sin(azimuth)
        nz = target.z + radius * math.cos(azimuth)
        ny = current_pos.y # Keep height const
        
        new_scene = copy.deepcopy(base_scene)
        if new_scene.camera:
            new_scene.camera.position = Vector3(x=nx, y=ny, z=nz)
            # Ensure target is same
            new_scene.camera.target = target
            
        frames.append(new_scene)
        
    return frames
