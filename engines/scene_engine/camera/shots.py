"""Camera Shot Language Engine (P7)."""
from __future__ import annotations

from enum import Enum
import math
from typing import Optional

from pydantic import BaseModel

from engines.scene_engine.core.scene_v2 import SceneV2
from engines.scene_engine.avatar.models import AvatarRigDefinition, AvatarBodyPart
from engines.scene_engine.core.geometry import Vector3
from engines.scene_engine.camera.service import create_orbit_camera_rig_for_node, attach_camera_rig_to_scene, CameraShotKind

class ShotSize(str, Enum):
    FULL_BODY = "full_body"
    MEDIUM_SHOT = "medium_shot" # Waist up
    CLOSE_UP = "close_up" # Head and shoulders
    EXTREME_CLOSE_UP = "extreme_close_up" # Eyes/Mouth

class ShotAngle(str, Enum):
    FRONT = "front"
    SIDE_PROFILE_LEFT = "side_profile_left"
    SIDE_PROFILE_RIGHT = "side_profile_right"
    THREE_QUARTER_LEFT = "three_quarter_left"
    THREE_QUARTER_RIGHT = "three_quarter_right"
    LOW_ANGLE = "low_angle"
    HIGH_ANGLE = "high_angle"

class ShotRequest(BaseModel):
    size: ShotSize = ShotSize.FULL_BODY
    angle: ShotAngle = ShotAngle.FRONT
    subject_shift: Vector3 = Vector3(x=0,y=0,z=0) # Rule of thirds offset

def apply_shot(scene: SceneV2, rig_def: AvatarRigDefinition, request: ShotRequest) -> SceneV2:
    """Configures the scene camera for the requested shot."""
    
    # 1. Determine Target Bone & Distance
    target_part = AvatarBodyPart.PELVIS
    distance = 3.0
    height_offset = 0.0
    
    if request.size == ShotSize.FULL_BODY:
        target_part = AvatarBodyPart.PELVIS
        distance = 3.5
        height_offset = 1.0 # Look at center mass
    elif request.size == ShotSize.MEDIUM_SHOT:
        target_part = AvatarBodyPart.TORSO # Or Spine
        distance = 2.0
        height_offset = 0.0 # Torso is usually higher than pelvis, bone location matters
    elif request.size == ShotSize.CLOSE_UP:
        target_part = AvatarBodyPart.HEAD
        distance = 0.8
        height_offset = 0.0
    elif request.size == ShotSize.EXTREME_CLOSE_UP:
        target_part = AvatarBodyPart.HEAD
        distance = 0.35
        height_offset = 0.05 # Look at eyes
        
    # Find bone node ID
    bone = next((b for b in rig_def.bones if b.part == target_part), None)
    # If not found (e.g. Torso missing), fallback to Root
    target_node_id = bone.node_id if bone else rig_def.root_bone_id
    
    # Map ShotSize to CameraShotKind (legacy service map)
    # or just use create_orbit_camera directly with manual params.
    # We will use create_orbit_camera... but we need angle logic.
    
    # Calculate Angle Offset
    # Orbit rig assumes Z distance.
    # We can rotate the camera position around the target.
    
    azimuth = 0.0 # Radians. 0 = Front (+Z looking at -Z? No, orbit logic was Z+distance)
    elevation = 0.0
    
    if request.angle == ShotAngle.SIDE_PROFILE_LEFT:
        azimuth = -math.pi / 2
    elif request.angle == ShotAngle.SIDE_PROFILE_RIGHT:
        azimuth = math.pi / 2
    elif request.angle == ShotAngle.THREE_QUARTER_LEFT:
        azimuth = -math.pi / 4
    elif request.angle == ShotAngle.THREE_QUARTER_RIGHT:
        azimuth = math.pi / 4
    elif request.angle == ShotAngle.LOW_ANGLE:
        elevation = -0.3 # Radians
    elif request.angle == ShotAngle.HIGH_ANGLE:
        elevation = 0.5
        
    # Use existing service to get base rig?
    # Actually existing service `create_orbit_camera_rig_for_node` puts cam at (target.x, target.y+h, target.z+d).
    # That creates a Front shot (assuming mesh faces +Z? wait, usually mesh faces +Z or -Z).
    # If mesh faces +Z, and cam is at +Z looking at 0, it sees the BACK.
    # Standard: Character faces +Z. Camera at +Z looking -Z sees BACK.
    # Character faces -Z (glTF standard often +Z is forward? No +Z is Front in some, -Z in others. Unity +Z=Forward).
    # Northstar P0 analysis: primitive ops create standard box.
    # Let's assume Front = Camera at (0, h, distance) looking at (0, h, 0).
    
    # We manually build the rig here to support angles.
    from engines.scene_engine.camera.service import _get_node_world_position, Camera, CameraProjection, Light, LightKind, CameraRig
    import uuid
    
    t_pos = _get_node_world_position(scene, target_node_id)
    if not t_pos: t_pos = Vector3(x=0,y=0,z=0)
    
    # Target center = t_pos + height_offset (local offset usually 0 if bone is correct, but bone pivots vary)
    # Usually Head pivot is at base of neck. Eye level is +0.1.
    final_target = Vector3(
        x=t_pos.x + request.subject_shift.x + (0 if target_part != AvatarBodyPart.PELVIS else 0), 
        y=t_pos.y + height_offset + request.subject_shift.y,
        z=t_pos.z + request.subject_shift.z
    )
    
    # Camera Pos on Sphere
    # cx = distance * sin(azimuth) * cos(elevation)
    # cy = distance * sin(elevation)
    # cz = distance * cos(azimuth) * cos(elevation)
    cx = distance * math.sin(azimuth) * math.cos(elevation)
    cy = distance * math.sin(elevation)
    cz = distance * math.cos(azimuth) * math.cos(elevation)
    
    # Add to target
    cam_pos = Vector3(
        x=final_target.x + cx,
        y=final_target.y + cy,
        z=final_target.z + cz
    )
    
    camera = Camera(
        id=f"cam_{uuid.uuid4().hex[:8]}",
        projection=CameraProjection.PERSPECTIVE,
        fov_deg=35.0 if request.size in [ShotSize.CLOSE_UP, ShotSize.EXTREME_CLOSE_UP] else 50.0,
        position=cam_pos,
        target=final_target
    )
    
    # Standard Lights (Key+Fill)
    lights = [
        Light(id="key", kind=LightKind.DIRECTIONAL, position=Vector3(x=2, y=4, z=2), direction=Vector3(x=-0.5, y=-1, z=-0.5)),
        Light(id="fill", kind=LightKind.DIRECTIONAL, position=Vector3(x=-2, y=2, z=2), intensity=0.5)
    ]
    
    rig = CameraRig(camera=camera, lights=lights)
    return attach_camera_rig_to_scene(scene, rig)
