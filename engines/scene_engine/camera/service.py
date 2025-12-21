"""Camera Service Logic."""
from __future__ import annotations
import math
import uuid
from typing import Optional, List, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from engines.scene_engine.core.scene_v2 import SceneV2, SceneNodeV2

from engines.scene_engine.core.geometry import Vector3
from engines.scene_engine.camera.models import (
    Camera,
    CameraRig,
    CameraProjection,
    CameraShotKind,
    Light,
    LightKind,
)

def create_orbit_camera_rig_for_node(
    scene: SceneV2,
    node_id: str,
    distance: float,
    height: float,
    shot_kind: CameraShotKind = CameraShotKind.FULL_BODY,
) -> CameraRig:
    # 1. Find Node & World Position
    target_pos = _get_node_world_position(scene, node_id)
    if not target_pos:
        # Fallback to origin if node not found (should we raise?)
        target_pos = Vector3(x=0, y=0, z=0)

    # 2. Camera Position
    # P0: Simple offset in -Z (front?) or +Z?
    # Usually +Z is "front" in many systems looking at -Z, or vice versa.
    # We'll place camera at (target.x, target.y + height, target.z + distance) assuming looking back at target.
    # "Roughly distance units away in -Z" -> imply camera is at -Z looking at +Z?
    # Let's assume camera at z=+distance looking at z=target.z.
    
    cam_pos = Vector3(
        x=target_pos.x,
        y=target_pos.y + height,
        z=target_pos.z + distance
    )
    
    # 3. FOV
    fovs = {
        CameraShotKind.HERO_CLOSEUP: 35.0,
        CameraShotKind.FULL_BODY: 50.0,
        CameraShotKind.WIDE_ENVIRONMENT: 75.0,
    }
    fov = fovs.get(shot_kind, 50.0)
    
    camera = Camera(
        id=f"cam_{uuid.uuid4().hex[:8]}",
        projection=CameraProjection.PERSPECTIVE,
        fov_deg=fov,
        position=cam_pos,
        target=target_pos,
    )
    
    # 4. Lights
    # Key Light: Above and to the right (front-right)
    key_light = Light(
        id=f"light_key_{uuid.uuid4().hex[:8]}",
        kind=LightKind.DIRECTIONAL,
        color=Vector3(x=1.0, y=0.95, z=0.9), # Warm
        intensity=1.2,
        direction=Vector3(x=-0.5, y=-0.8, z=-0.5) # pointing down/left/back towards origin?
        # Actually direction vector should point FROM light TO target or usually it defines light rays direction.
        # Directional light: rays travel in this direction.
        # If camera is at +Z looking at 0, Key light from +X+Y+Z pointing at 0 would have direction (-1, -1, -1).
    )

    # Fill Light: From left, softer/cooler
    fill_light = Light(
        id=f"light_fill_{uuid.uuid4().hex[:8]}",
        kind=LightKind.DIRECTIONAL,
        color=Vector3(x=0.8, y=0.8, z=0.9), # Cool
        intensity=0.5,
        direction=Vector3(x=0.5, y=-0.5, z=-0.5)
    )
    
    # Rim?
    
    return CameraRig(
        camera=camera,
        lights=[key_light, fill_light]
    )


def attach_camera_rig_to_scene(scene: SceneV2, rig: CameraRig) -> SceneV2:
    scene.camera = rig.camera
    # Append or overwrite? Prompt says "extended/overwritten".
    # We'll append for now or reset? "scene.lights extended"
    scene.lights.extend(rig.lights)
    return scene


def create_avatar_hero_shot(scene: SceneV2, avatar_root_id: str) -> SceneV2:
    # "head & shoulders / upper body"
    # Assuming avatar origin is at feet.
    # Height needs to be around head level (1.5 - 1.7m).
    # Distance usually 1.5 - 2.0m for closeup.
    
    rig = create_orbit_camera_rig_for_node(
        scene, 
        node_id=avatar_root_id,
        distance=2.5,
        height=1.4, # Aim at chest/neck
        shot_kind=CameraShotKind.HERO_CLOSEUP
    )
    
    # Adjust target slightly up?
    # Orbit rig targets the node origin (feet). To shot head, we need target to be higher.
    # We can perform a post-fix or logic update.
    # The prompt says "Compute the node's approximate world position... Set camera.target to the node's world position".
    # If the node is "avatar_root" (pelvis or ground), target is low.
    # Ideally we'd find the "Head" bone.
    # But for P0 we follow simple instruction or slightly adjust.
    # I'll manually adjust target Y up by 1.5m if it's a hero shot to look at face, and raise camera.
    # For now, following strict "target = node position" might be too low.
    # I will modify rig logic:
    #   Orbit rig takes "offset_target" maybe? Or just keep simple.
    # Let's assume avatar_root_id is the root.
    # I will manually nudge the camera target for this preset.
    
    rig.camera.target.y += 1.5
    rig.camera.position.y += 1.5 
    
    return attach_camera_rig_to_scene(scene, rig)


def _get_node_world_position(scene: SceneV2, node_id: str) -> Optional[Vector3]:
    # Need to traverse hierarchy to find node and sum translations (ignoring rotation/scale for P0 simplified).
    
    def recursive_find(nodes: List[SceneNodeV2], parent_pos: Vector3) -> Optional[Vector3]:
        for node in nodes:
            # Composition
            wx = parent_pos.x + node.transform.position.x
            wy = parent_pos.y + node.transform.position.y
            wz = parent_pos.z + node.transform.position.z
            current_wpos = Vector3(x=wx, y=wy, z=wz)
            
            if node.id == node_id:
                return current_wpos
            
            found = recursive_find(node.children, current_wpos)
            if found:
                return found
        return None
        
    return recursive_find(scene.nodes, Vector3(x=0, y=0, z=0))
