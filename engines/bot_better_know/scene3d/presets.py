"""Bot Better Know - Project Specific 3D Presets."""
from __future__ import annotations

import copy
import uuid
from enum import Enum
from typing import Optional, Tuple

from pydantic import BaseModel

from engines.scene_engine.core.geometry import (
    BoxParams,
    CylinderParams,
    EulerAngles,
    Material,
    Transform,
    Vector3,
)
from engines.scene_engine.core.primitives import (
    build_box_mesh,
    build_cylinder_mesh,
)
from engines.scene_engine.core.scene_v2 import (
    ConstructionOp,
    ConstructionOpKind,
    SceneNodeV2,
    SceneV2,
)
from engines.scene_engine.core.types import Camera
from engines.scene_engine.environment.models import (
    EnvPrimitiveKind,
    OpeningParams,
    RoomParams,
)
from engines.scene_engine.environment.service import (
    add_opening_on_wall,
    build_room,
)
from engines.scene_engine.avatar.models import (
    AvatarBodyPart,
    AvatarRigDefinition,
)
from engines.scene_engine.avatar.service import (
    build_default_avatar,
)
from engines.scene_engine.camera.models import (
    CameraShotKind, 
    CameraRig,
)
from engines.scene_engine.camera.service import (
    create_orbit_camera_rig_for_node,
    attach_camera_rig_to_scene,
)
from engines.scene_engine.io.gltf_import import gltf_bytes_to_scene_v2
from engines.scene_engine.constraints.models import SceneConstraint, ConstraintKind
from engines.scene_engine.constraints.service import solve_constraints
from engines.scene_engine.params.models import (
    ParamGraph, ParamNode, ParamNodeKind, 
    ParamBinding, ParamTargetKind
)
from engines.scene_engine.params.service import evaluate_param_graph, apply_param_bindings
from engines.scene_engine.params.models import (
    ParamGraph, ParamNode, ParamNodeKind, 
    ParamBinding, ParamTargetKind
)
from engines.scene_engine.params.service import evaluate_param_graph, apply_param_bindings



# --- Grime Pirate Radio Definitions ---

class GrimeStudioVariant(str, Enum):
    PIRATE_ROOFTOP_V1 = "pirate_rooftop_v1"


class GrimeStudioStyle(BaseModel):
    variant: GrimeStudioVariant = GrimeStudioVariant.PIRATE_ROOFTOP_V1
    room_width: float = 3.0
    room_depth: float = 4.0
    room_height: float = 2.4
    roof_size: float = 10.0
    wall_thickness: float = 0.2
    grime_level: float = 0.7
    clutter_level: float = 0.6


def _vec3(x, y, z) -> Vector3:
    return Vector3(x=float(x), y=float(y), z=float(z))


def _transform(x=0, y=0, z=0, rx=0, ry=0, rz=0, s=1) -> Transform:
    return Transform(
        position=_vec3(x, y, z),
        rotation=EulerAngles(x=float(rx), y=float(ry), z=float(rz)),
        scale=_vec3(s, s, s)
    )

def _create_node(name: str, mesh_id: str, transform: Transform, meta: dict) -> SceneNodeV2:
    # Ensure project tag
    meta["project"] = "bot-better-know"
    return SceneNodeV2(
        id=f"node_{uuid.uuid4().hex[:8]}",
        name=name,
        transform=transform,
        mesh_id=mesh_id,
        meta=meta
    )


def build_grime_pirate_rooftop_scene(style: Optional[GrimeStudioStyle] = None) -> SceneV2:
    if style is None:
        style = GrimeStudioStyle()

    # 1. Base Scene
    base_scene = SceneV2(
        id=uuid.uuid4().hex,
        nodes=[], meshes=[], materials=[],
        # camera=None
        history=[]
    )
    
    # 2. Roof Slab
    mesh_roof = build_box_mesh(BoxParams(width=style.roof_size, height=0.5, depth=style.roof_size))
    base_scene.meshes.append(mesh_roof)
    
    node_roof = _create_node(
        "RoofSlab", mesh_roof.id,
        _transform(x=0, y=-0.25, z=0),
        {"env_kind": "ROOF_SLAB", "preset": style.variant.value, "grime_level": style.grime_level}
    )
    base_scene.nodes.append(node_roof)
    
    # 3. Shack Room
    room_origin = Vector3(x=2.0, y=0.0, z=2.0)
    
    room_params = RoomParams(
        width=style.room_width,
        depth=style.room_depth,
        height=style.room_height,
        wall_thickness=style.wall_thickness,
        origin=room_origin
    )
    
    # Build room (generic)
    room_scene, parts = build_room(base_scene, room_params) 
    scene = room_scene
    
    # Tag room nodes
    for part_name, nid in parts.items():
        node = next(n for n in scene.nodes if n.id == nid)
        node.meta["project"] = "bot-better-know" # Add project tag
        node.meta["env_kind"] = "ROOM"
        node.meta["room_role"] = "pirate_radio_shack"
        node.meta["preset"] = style.variant.value
        
    # 4. Access Door
    wall_id = parts.get("wall_-x") # Side wall
    if wall_id:
        open_params = OpeningParams(
            width=0.9, height=2.0, sill_height=0.0, offset_along_wall=0.5
        )
        scene = add_opening_on_wall(scene, wall_id, open_params, EnvPrimitiveKind.DOOR_OPENING)
        # Tag new opening
        wall = next(n for n in scene.nodes if n.id == wall_id)
        if wall.children:
            door_node = wall.children[-1]
            door_node.meta["project"] = "bot-better-know"
            door_node.meta["role"] = "roof_access_door"
            door_node.meta["preset"] = style.variant.value

    # 5. Radio Desk + Equipment
    mesh_desk = build_box_mesh(BoxParams(width=1.8, height=0.8, depth=0.6))
    scene.meshes.append(mesh_desk)
    
    desk_pos = _vec3(
        x=room_origin.x, 
        y=0.4, 
        z=room_origin.z + (style.room_depth / 2.0) - 0.6 
    )
    
    node_desk = _create_node(
        "RadioDesk", mesh_desk.id,
        _transform(x=desk_pos.x, y=desk_pos.y, z=desk_pos.z),
        {"env_kind": "TABLE", "role": "radio_desk", "preset": style.variant.value}
    )
    scene.nodes.append(node_desk)
    
    # Equipment on desk
    mesh_equip = build_box_mesh(BoxParams(width=0.4, height=0.2, depth=0.3))
    scene.meshes.append(mesh_equip)
    
    e1 = _create_node(
        "Mixer", mesh_equip.id,
        _transform(x=desk_pos.x - 0.4, y=0.9, z=desk_pos.z),
        {"env_kind": "EQUIPMENT", "equipment_kind": "mixer", "preset": style.variant.value}
    )
    e2 = _create_node(
        "Transmitter", mesh_equip.id,
        _transform(x=desk_pos.x + 0.5, y=0.9, z=desk_pos.z),
        {"env_kind": "EQUIPMENT", "equipment_kind": "transmitter_box", "preset": style.variant.value}
    )
    scene.nodes.extend([e1, e2])

    # 6. Mic Stand / MC Spot
    mesh_mic_stand = build_cylinder_mesh(CylinderParams(radiusTop=0.02, radiusBottom=0.02, height=1.4))
    mesh_mic_head = build_box_mesh(BoxParams(width=0.1, height=0.1, depth=0.15))
    scene.meshes.extend([mesh_mic_stand, mesh_mic_head])
    
    mc_pos = _vec3(x=desk_pos.x, y=0.7, z=desk_pos.z - 1.2)
    
    node_mic_base = _create_node(
        "MicStand", mesh_mic_stand.id,
        _transform(x=mc_pos.x, y=mc_pos.y, z=mc_pos.z),
        {"env_kind": "MIC_STAND", "role": "mc_spot", "preset": style.variant.value}
    )
    
    node_mic_head = SceneNodeV2(
        id=f"mic_head_{uuid.uuid4().hex[:8]}",
        name="Mic", 
        transform=_transform(y=0.7),
        mesh_id=mesh_mic_head.id,
        meta={"env_kind": "MIC", "project": "bot-better-know"}
    )
    node_mic_base.children.append(node_mic_head)
    scene.nodes.append(node_mic_base)
    
    # 7. Clutter
    mesh_crate = build_box_mesh(BoxParams(width=0.4, height=0.4, depth=0.4))
    scene.meshes.append(mesh_crate)
    
    if style.clutter_level > 0:
        crate = _create_node(
            "Crate", mesh_crate.id,
            _transform(x=room_origin.x - 1.0, y=0.2, z=room_origin.z - 1.0),
            {"env_kind": "CLUTTER", "clutter_level": style.clutter_level, "preset": style.variant.value}
        )
        scene.nodes.append(crate)
        
    # 8. Antenna on Roof
    mesh_mast = build_cylinder_mesh(CylinderParams(radiusTop=0.05, radiusBottom=0.05, height=4.0))
    scene.meshes.append(mesh_mast)
    
    ant_pos = _vec3(x=-3.0, y=2.0, z=-3.0)
    node_ant = _create_node(
        "PirateAntenna", mesh_mast.id,
        _transform(x=ant_pos.x, y=ant_pos.y, z=ant_pos.z),
        {"env_kind": "ANTENNA", "role": "pirate_broadcast_aerial", "preset": style.variant.value}
    )
    scene.nodes.append(node_ant)
    
    scene.history.append(ConstructionOp(
        id=f"op_{uuid.uuid4().hex}",
        kind=ConstructionOpKind.CREATE_PRIMITIVE,
        params={"type": "grime_pirate_rooftop", "style": style.model_dump()}
    ))
    
    return scene


def center_mc_spot_in_room(scene: SceneV2) -> SceneV2:
    desk = next((n for n in scene.nodes if n.meta.get("role") == "radio_desk"), None)
    if not desk:
        return scene
        
    mic = next((n for n in scene.nodes if n.meta.get("role") == "mc_spot"), None)
    if not mic:
        return scene
        
    target_z = desk.transform.position.z - 1.5
    target_x = desk.transform.position.x 
    
    mic.transform.position.x = target_x
    mic.transform.position.z = target_z
    
    return scene


# --- Android MC Avatar Definitions ---

class AndroidAvatarVariant(str, Enum):
    ANDROID_MC_V1 = "android_mc_v1"


class AndroidAvatarStyle(BaseModel):
    variant: AndroidAvatarVariant = AndroidAvatarVariant.ANDROID_MC_V1
    height: float = 1.8
    head_scale: float = 1.1
    torso_width: float = 0.4
    limb_thickness: float = 0.12
    accent_color: Optional[str] = None
    base_color: Optional[str] = None
    metallicity: Optional[float] = 0.7
    roughness: Optional[float] = 0.3


def _vec3_from_hex(hex_str: str) -> Vector3:
    hex_str = hex_str.lstrip("#")
    if len(hex_str) == 3:
        hex_str = "".join([c * 2 for c in hex_str])
    r = int(hex_str[0:2], 16) / 255.0
    g = int(hex_str[2:4], 16) / 255.0
    b = int(hex_str[4:6], 16) / 255.0
    return Vector3(x=r, y=g, z=b)


def build_android_mc_avatar(style: Optional[AndroidAvatarStyle] = None) -> Tuple[SceneV2, AvatarRigDefinition]:
    if style is None:
        style = AndroidAvatarStyle()

    # 1. Build Base
    scene, rig = build_default_avatar()
    
    # Tag nodes with project
    def tag_nodes(nodes):
        for n in nodes:
            n.meta["project"] = "bot-better-know"
            tag_nodes(n.children)
    tag_nodes(scene.nodes)
    
    # 2. Define Materials
    mat_base_id = f"mat_base_{uuid.uuid4().hex[:8]}"
    base_col = _vec3_from_hex(style.base_color) if style.base_color else Vector3(x=0.2, y=0.2, z=0.2)
    mat_base = Material(
        id=mat_base_id,
        name="AndroidBase",
        base_color=base_col,
        metallic=style.metallicity,
        roughness=style.roughness,
        meta={"style": style.variant.value, "project": "bot-better-know"}
    )
    
    mat_accent_id = f"mat_accent_{uuid.uuid4().hex[:8]}"
    accent_col = _vec3_from_hex(style.accent_color) if style.accent_color else Vector3(x=0.0, y=1.0, z=0.9)
    mat_accent = Material(
        id=mat_accent_id,
        name="AndroidAccent",
        base_color=accent_col,
        metallic=style.metallicity,
        roughness=style.roughness,
        emissive=accent_col,
        meta={"style": style.variant.value, "project": "bot-better-know"}
    )
    
    scene.materials.extend([mat_base, mat_accent])
    
    # Flatten
    def _flatten_nodes(nodes):
        flat = []
        for n in nodes:
            flat.append(n)
            flat.extend(_flatten_nodes(n.children))
        return flat
        
    node_map = {node.id: node for node in _flatten_nodes(scene.nodes)}
    bone_map = {b.part: node_map[b.node_id] for b in rig.bones if b.node_id in node_map}
    
    # 3. Modify Geometry
    
    # Head
    if AvatarBodyPart.HEAD in bone_map:
        head_node = bone_map[AvatarBodyPart.HEAD]
        head_node.material_id = mat_base_id
        s = style.head_scale
        head_node.transform.scale = Vector3(x=s, y=s, z=s) 
        head_node.meta["avatar_kind"] = style.variant.value
        head_node.meta["body_part"] = AvatarBodyPart.HEAD.value
        
    # Torso
    if AvatarBodyPart.TORSO in bone_map:
        torso = bone_map[AvatarBodyPart.TORSO]
        torso.material_id = mat_accent_id
        torso.meta["avatar_kind"] = style.variant.value
        torso.meta["body_part"] = AvatarBodyPart.TORSO.value
        
        mesh_torso = build_box_mesh(BoxParams(width=style.torso_width, height=0.5, depth=0.25))
        scene.meshes.append(mesh_torso)
        torso.mesh_id = mesh_torso.id
        
    # Limbs
    limb_parts = [
        AvatarBodyPart.ARM_L_UPPER, AvatarBodyPart.ARM_L_LOWER,
        AvatarBodyPart.ARM_R_UPPER, AvatarBodyPart.ARM_R_LOWER,
        AvatarBodyPart.LEG_L_UPPER, AvatarBodyPart.LEG_L_LOWER,
        AvatarBodyPart.LEG_R_UPPER, AvatarBodyPart.LEG_R_LOWER,
    ]
    
    for part in limb_parts:
        if part in bone_map:
            node = bone_map[part]
            node.material_id = mat_base_id
            node.meta["avatar_kind"] = style.variant.value
            node.meta["body_part"] = part.value

    # Hands/Feet
    for part in [AvatarBodyPart.HAND_L, AvatarBodyPart.HAND_R, AvatarBodyPart.FOOT_L, AvatarBodyPart.FOOT_R]:
        if part in bone_map:
            n = bone_map[part]
            n.material_id = mat_accent_id
            n.meta["avatar_kind"] = style.variant.value
            n.meta["body_part"] = part.value

    if not scene.history:
        scene.history = []
    
    scene.history.append(ConstructionOp(
        id=f"op_{uuid.uuid4().hex}",
        kind=ConstructionOpKind.CREATE_PRIMITIVE,
        params={"type": "android_mc_avatar", "style": style.model_dump()}
    ))
    
    return scene, rig


def insert_android_mc_avatar(scene: SceneV2, style: Optional[AndroidAvatarStyle] = None) -> Tuple[SceneV2, AvatarRigDefinition]:
    avatar_scene, rig = build_android_mc_avatar(style)
    new_scene = copy.deepcopy(scene)
    new_scene.meshes.extend(avatar_scene.meshes)
    new_scene.materials.extend(avatar_scene.materials)
    new_scene.nodes.extend(avatar_scene.nodes)
    
    if new_scene.history:
        new_scene.history.extend(avatar_scene.history or [])
        
    return new_scene, rig


def build_bbk_android_mc_avatar_full_gas() -> Tuple[SceneV2, AvatarRigDefinition]:
    """
    Builds a 'Full Gas' showcase of the Android MC avatar.
    - Custom Style (Heavy, Metallic).
    - Ground plane.
    - Performance Pose.
    - Enhanced geometry details.
    """
    from engines.scene_engine.avatar.style import AvatarStyleParams, BodyBuild, apply_avatar_style
    
    # 1. High-Spec Style
    style_spec = AvatarStyleParams(
        height=1.95, 
        body_build=BodyBuild.HEAVY, 
        has_shoulder_pads=True,
        has_hood=False,  # Show the head
        has_visor=True,
        # We can pass custom meta for advanced materials if the engine supports it
        # or use the style's potential future material fields. 
        # For now, we manually tune materials after build.
    )

    # 2. Build Base Avatar
    # Use existing builder as base, but we will upgrade it.
    android_style = AndroidAvatarStyle(
        variant=AndroidAvatarVariant.ANDROID_MC_V1,
        base_color="#1A1A1A",     # Dark metallic grey
        accent_color="#00FFAA",   # Cyber cyan/teal
        metallicity=0.9,
        roughness=0.15
    )
    
    scene, rig = build_android_mc_avatar(android_style)
    
    # Apply Generic Engine Style (Geometry Scaling)
    scene = apply_avatar_style(scene, rig, style_spec)
    
    # 3. Add Studio Ground Plane
    mesh_floor = build_box_mesh(BoxParams(width=20.0, height=0.1, depth=20.0))
    scene.meshes.append(mesh_floor)
    
    floor_node = _create_node(
        "StudioFloor", 
        mesh_floor.id,
        _transform(x=0, y=-0.05, z=0),
        {"env_kind": "ROOF_SLAB", "role": "studio_floor", "project": "bot-better-know"} 
        # Reusing ROOF_SLAB kind so our viewer renders it as the floor plane
    )
    scene.nodes.insert(0, floor_node) # Put at start
    
    # 4. Pose the Avatar (Manual Bone Transforms)
    # We need to find the bone nodes.
    # We can use the rig definition for this.
    
    def find_bone_node(part: AvatarBodyPart):
        bone = next((b for b in rig.bones if b.part == part), None)
        if bone:
            return next((n for n in scene.nodes if n.id == bone.node_id), None)
            # Note: scenes are flat list in V2 usually? 
            # build_default_avatar returns a tree. 
            # We need to traverse slightly if not flat. 
            # But wait, `build_android_mc_avatar` does not flatten?
            # It just modifies geometry.
            
            # Helper to find node in tree
            def _find(nodes, nid):
                for n in nodes:
                    if n.id == nid: return n
                    found = _find(n.children, nid)
                    if found: return found
                return None
            
            return _find(scene.nodes, bone.node_id)
        return None

    # Pose: Mic Performance
    # Left Arm: Raised forward (holding mic)
    # Right Arm: Relaxed down/side
    # Head: Tilted slightly down
    
    # Shoulder L (Upper Arm)
    arm_l = find_bone_node(AvatarBodyPart.ARM_L_UPPER)
    if arm_l:
        # Raise arm forward approx 45-60 deg
        # Euler angles in degrees or radians? 
        # Geometry types usually assume Radians for math but EulerAngles struct... 
        # let's assume Radians. 45 deg = 0.78 rad.
        # Rotating around X (up/down) and Z (out).
        # Assuming T-Pose or A-Pose default? Usually A-Pose (arms down-ish).
        # Let's try rotating X -1.5 (forward up)
        arm_l.transform.rotation.x = -1.2 
        arm_l.transform.rotation.z = -0.2

    # Elbow L (Lower Arm)
    forearm_l = find_bone_node(AvatarBodyPart.ARM_L_LOWER)
    if forearm_l:
        # Bend elbow inward/up
        forearm_l.transform.rotation.x = -1.0 # Bend 
    
    # Head
    head = find_bone_node(AvatarBodyPart.HEAD)
    if head:
        # Tilt down slightly
        head.transform.rotation.x = 0.3
        # Look slightly left
        head.transform.rotation.y = 0.2
        
    # Legs (Stance)
    leg_l = find_bone_node(AvatarBodyPart.LEG_L_UPPER)
    leg_r = find_bone_node(AvatarBodyPart.LEG_R_UPPER)
    
    if leg_l:
        leg_l.transform.rotation.x = -0.2 # Step forward
        leg_l.transform.rotation.z = 0.1  # Wide stance
        
    if leg_r:
        leg_r.transform.rotation.x = 0.2  # Step back
        leg_r.transform.rotation.z = -0.1 # Wide stance
        
    # 5. Camera Hint
    # Place a node representing optimal camera view
    cam_node = SceneNodeV2(
        id=f"cam_hint_{uuid.uuid4().hex[:8]}",
        name="CameraHint",
        transform=_transform(x=1.5, y=1.6, z=2.5), # Front-right view
        meta={"role": "camera_primary", "target": "avatar_root"}
    )
    scene.nodes.append(cam_node)

    return scene, rig


# --- Hero Avatar + Beauty Env ---

class HeroAvatarPresetKind(str, Enum):
    GENERIC_ANDROID_V1 = "generic_android_v1"


def load_bbk_hero_avatar_scene_v2(
    preset: HeroAvatarPresetKind = HeroAvatarPresetKind.GENERIC_ANDROID_V1,
) -> SceneV2:
    """Loads the hero avatar GLB and preps it for the scene."""
    
    # Path to asset
    import os
    
    # Try relative to this file first
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # engines/bot_better_know
    asset_path = os.path.join(base_dir, "assets", "hero_android_v1.glb")
    
    if not os.path.exists(asset_path):
        # Fallback check current working dir
        if os.path.exists("engines/bot_better_know/assets/hero_android_v1.glb"):
            asset_path = "engines/bot_better_know/assets/hero_android_v1.glb"
        else:
            raise FileNotFoundError(f"Hero asset not found at {asset_path}")

    with open(asset_path, "rb") as f:
        data = f.read()

    scene = gltf_bytes_to_scene_v2(data)
    
    # Tag root nodes
    for node in scene.nodes:
        # Assuming top level nodes are roots of the imported model
        node.meta["project"] = "bot_better_know"
        node.meta["role"] = "hero_avatar"
        node.meta["kind"] = preset.value

    return scene


def build_bbk_beauty_environment() -> SceneV2:
    """Builds a beauty environment (ground plane + backdrop)."""
    scene = SceneV2(
        id=uuid.uuid4().hex,
        nodes=[], meshes=[], materials=[],
        # camera=None
    )
    
    # Ground Plane
    mesh_ground = build_box_mesh(BoxParams(width=50.0, height=0.1, depth=50.0))
    scene.meshes.append(mesh_ground)
    
    mat_ground = Material(
        id=f"mat_ground_{uuid.uuid4().hex[:8]}",
        name="BeautyGround",
        base_color=Vector3(x=0.2, y=0.25, z=0.2), # Dark Greenish/Grey
        roughness=0.8,
        meta={"project": "bot_better_know"}
    )
    scene.materials.append(mat_ground)
    
    node_ground = SceneNodeV2(
        id=f"ground_{uuid.uuid4().hex[:8]}",
        name="Ground",
        transform=_transform(x=0, y=-0.05, z=0),
        mesh_id=mesh_ground.id,
        material_id=mat_ground.id,
        meta={"env_kind": "beauty_ground", "project": "bot_better_know"}
    )
    scene.nodes.append(node_ground)
    
    # Simple Backdrop (Vertical Plane/Box)
    mesh_sky = build_box_mesh(BoxParams(width=50.0, height=20.0, depth=0.1))
    scene.meshes.append(mesh_sky)
    
    mat_sky = Material(
        id=f"mat_sky_{uuid.uuid4().hex[:8]}",
        name="BeautySky",
        base_color=Vector3(x=0.53, y=0.81, z=0.92), # Sky Blue
        roughness=1.0, 
        emissive=Vector3(x=0.1, y=0.15, z=0.2), # Slight emission
        meta={"project": "bot_better_know"}
    )
    scene.materials.append(mat_sky)
    
    node_sky = SceneNodeV2(
        id=f"sky_{uuid.uuid4().hex[:8]}",
        name="SkyBackdrop",
        transform=_transform(x=0, y=10.0, z=-20.0), # Behind
        mesh_id=mesh_sky.id,
        material_id=mat_sky.id,
        meta={"env_kind": "beauty_backdrop", "project": "bot_better_know"}
    )
    scene.nodes.append(node_sky)
    
    # Scene Meta
    scene.environment = {
        "kind": "beauty_landscape",
        "sky_color": "#87CEEB",
        "meta": {"project": "bot_better_know"}
    }
    
    return scene


def build_bbk_hero_avatar_beauty_scene() -> SceneV2:
    """Composes Hero Avatar + Beauty Environment + Camera Rig."""
    
    # 1. Load Components
    avatar_scene = load_bbk_hero_avatar_scene_v2()
    env_scene = build_bbk_beauty_environment()
    
    # 2. Merge Scenes
    final_scene = SceneV2(
        id=uuid.uuid4().hex,
        nodes=env_scene.nodes + avatar_scene.nodes,
        meshes=env_scene.meshes + avatar_scene.meshes,
        materials=env_scene.materials + avatar_scene.materials,
        environment=env_scene.environment
        # camera=None
    )
    
    # 3. Find Avatar Root for Camera Target
    # We tagged it with role="hero_avatar"
    avatar_root = next((n for n in final_scene.nodes if n.meta.get("role") == "hero_avatar"), None)
    
    if avatar_root is None:
        pass
        
    if avatar_root:
        # 4. Create Camera Rig
        rig = create_orbit_camera_rig_for_node(
            final_scene, 
            avatar_root.id, 
            distance=3.5, 
            height=1.4,
            shot_kind=CameraShotKind.FULL_BODY
        )
        
        # 5. Attach Rig
        final_scene = attach_camera_rig_to_scene(final_scene, rig)
        
    return final_scene


def build_bbk_rooftop_with_constraints() -> SceneV2:
    """Builds Rooftop + MC with physical constraints."""
    
    # 1. Base Components
    scene = build_grime_pirate_rooftop_scene()
    
    # Add Avatar
    # For constraints we want to compose properly. 
    # insert_android_mc_avatar returns (scene, rig). 
    # But insert_... does copy.deepcopy.
    
    # Let's use clean composition if possible.
    # insert_android_mc_avatar logic is: build avatar -> extend scene.
    scene, rig = insert_android_mc_avatar(scene)
    
    # 2. Identify Nodes
    
    # Mic Spot
    mic_node = next((n for n in scene.nodes if n.meta.get("role") == "mc_spot"), None)
    
    # Mic Head (for aiming)
    mic_head = None
    if mic_node and mic_node.children:
        mic_head = mic_node.children[0] # assuming first child is head
        
    # Avatar Root (Pelvis/Base)
    # The insert function doesn't return the root node easily, but rig does.
    # rig.bones has node_ids.
    # Usually root is not in bones if it's a container.
    # But we can find body parts.
    
    # Helper to find node by ID in flat or tree
    def find_node(nid):
        def _f(nodes):
            for n in nodes:
                if n.id == nid: return n
                found = _f(n.children)
                if found: return found
            return None
        return _f(scene.nodes)

    head_bone = next((b for b in rig.bones if b.part == AvatarBodyPart.HEAD), None)
    head_node = find_node(head_bone.node_id) if head_bone else None
    
    torso_bone = next((b for b in rig.bones if b.part == AvatarBodyPart.TORSO), None)
    torso_node = find_node(torso_bone.node_id) if torso_bone else None
    
    # 3. Apply Constraints
    
    # A. Torso/Body near Mic
    if torso_node and mic_node:
        scene.constraints.append(SceneConstraint(
            id=f"c_dist_{uuid.uuid4().hex[:8]}",
            kind=ConstraintKind.MAINTAIN_DISTANCE,
            node_id=torso_node.id,
            target_node_id=mic_node.id,
            distance=0.8
        ))
        
    # B. Head aimed at Mic
    if head_node and mic_head:
        scene.constraints.append(SceneConstraint(
            id=f"c_aim_{uuid.uuid4().hex[:8]}",
            kind=ConstraintKind.AIM_AT_NODE,
            node_id=head_node.id,
            target_node_id=mic_head.id
        ))
        
    # C. Feet on Floor (y=0 relative to roof slab? Roof is at -0.25, top surface at 0.0)
    # Let's say floor is at 0.0
    for part in [AvatarBodyPart.FOOT_L, AvatarBodyPart.FOOT_R]:
        bone = next((b for b in rig.bones if b.part == part), None)
        if bone:
            n = find_node(bone.node_id)
            if n:
                scene.constraints.append(SceneConstraint(
                    id=f"c_floor_{part.value}",
                    kind=ConstraintKind.KEEP_ON_PLANE,
                    node_id=n.id,
                    plane_normal=Vector3(x=0, y=1, z=0),
                    plane_offset=0.0
                ))

    # 4. Solves
    solved_scene = solve_constraints(scene)
    return solved_scene


def build_bbk_hero_avatar_beauty_scene_constrained() -> SceneV2:
    """Hero scene with constraints (Feet on ground)."""
    scene = build_bbk_hero_avatar_beauty_scene()
    
    # Find feet? We need the rig definition or heuristic.
    # The hero scene loader `load_bbk_hero_avatar_scene_v2` loads a glTF.
    # We didn't parse a RigDefinition from glTF yet.
    # So we don't strictly know which nodes are feet unless we search by name.
    # The generated asset has node names like "Triangle".
    # For the Constraint Engine Demo, we might need to rely on the Android MC preset instead 
    # if we want specific bone constraints, OR just constrain the root.
    
    # Let's constrain the root "hero_avatar" to be on plane y=0.
    
    root = next((n for n in scene.nodes if n.meta.get("role") == "hero_avatar"), None)
    if root:
        scene.constraints.append(SceneConstraint(
            id="c_root_floor",
            kind=ConstraintKind.KEEP_ON_PLANE,
            node_id=root.id,
            plane_normal=Vector3(x=0, y=1, z=0),
            plane_offset=0.0 
        ))
        
    solved_scene = solve_constraints(scene)
    return solved_scene


def build_bbk_mc_param_graph() -> ParamGraph:
    """
    Builds a graph with:
    - energy (0-1): Drives node Y (jump height) and scale.
    - mood (0-1): Drives color intensity.
    - camera_in_out (0-1): Drives camera distance.
    """
    
    # Nodes
    
    # 1. Inputs
    n_energy = ParamNode(id="in_energy", kind=ParamNodeKind.INPUT, params={"default": 0.5})
    n_mood = ParamNode(id="in_mood", kind=ParamNodeKind.INPUT, params={"default": 0.5})
    n_cam = ParamNode(id="in_cam", kind=ParamNodeKind.INPUT, params={"default": 0.5})
    
    # 2. Logic
    
    # Energy -> Jump Height (Remap 0-1 to 0-2.0)
    n_jump = ParamNode(
        id="op_jump", 
        kind=ParamNodeKind.REMAP, 
        inputs={"value": "in_energy"},
        params={"in_min": 0, "in_max": 1, "out_min": 0, "out_max": 2.0}
    )
    
    # Energy -> Scale (Remap 0-1 to 1.0-1.5)
    n_scale = ParamNode(
        id="op_scale",
        kind=ParamNodeKind.REMAP,
        inputs={"value": "in_energy"},
        params={"in_min": 0, "in_max": 1, "out_min": 1.0, "out_max": 1.5}
    )
    
    # Mood -> Color (Blue to Red?)
    # mood * 1.0 -> R
    # 1.0 - mood -> B 
    
    c_1 = ParamNode(id="c_1", kind=ParamNodeKind.CONSTANT, params={"value": 1.0})
    c_0 = ParamNode(id="c_0", kind=ParamNodeKind.CONSTANT, params={"value": 0.0})

    # R node
    n_r = ParamNode(id="op_r", kind=ParamNodeKind.MULTIPLY, inputs={"a": "in_mood", "b": "c_1"})
    # B node = 1.0 - mood. (No subtract node? use remap 0-1 to 1-0)
    n_b = ParamNode(
        id="op_b", 
        kind=ParamNodeKind.REMAP, 
        inputs={"value": "in_mood"}, 
        params={"in_min": 0, "in_max": 1, "out_min": 1, "out_max": 0}
    )
    
    n_color = ParamNode(
        id="op_color", 
        kind=ParamNodeKind.VECTOR_COMPOSE, 
        inputs={"x": "op_r", "y": "c_0", "z": "op_b"},
        params={"y": 0.5} # Green constant via params? Evaluator check? 
        # My evaluator for VECTOR_COMPOSE reads input X, Y, Z. 
        # If not linked, defaults to 0.0. 
        # I want Y=0.5. 
        # I need a constant for Y.
    )
    # Fix n_color: My evaluator doesn't read params for vector_compose fallback, it reads inputs.
    # So I need c_green.
    c_green = ParamNode(id="c_green", kind=ParamNodeKind.CONSTANT, params={"value": 0.5})
    n_color.inputs["y"] = "c_green"

    
    # Camera Dist (Remap 0-1 to 5.0 - 2.0)
    n_dist = ParamNode(
        id="op_dist",
        kind=ParamNodeKind.REMAP,
        inputs={"value": "in_cam"},
        params={"in_min": 0, "in_max": 1, "out_min": 5.0, "out_max": 2.0} # Closer as value increases
    )
    
    
    nodes = [n_energy, n_mood, n_cam, n_jump, n_scale, n_r, n_b, n_color, n_dist, c_1, c_0, c_green]
    
    return ParamGraph(
        id="bbk_param_graph",
        nodes=nodes,
        exposed_inputs={
            "energy": "in_energy",
            "mood": "in_mood",
            "camera_in_out": "in_cam"
        },
        outputs={
            "jump_height": "op_jump",
            "scale_augment": "op_scale",
            "mood_color": "op_color",
            "cam_distance": "op_dist"
        }
    )


def build_bbk_mc_parametric_scene(
    energy: float = 0.5, 
    mood: float = 0.0, 
    camera_in_out: float = 0.0
) -> Tuple[SceneV2, ParamGraph]:
    
    # 1. Base Scene
    scene, rig = insert_android_mc_avatar(build_grime_pirate_rooftop_scene())
    
    # 2. Graph
    graph = build_bbk_mc_param_graph()
    
    # 3. Define Bindings
    # Find Avatar Head
    head_node = next((n for n in scene.nodes if n.meta.get("body_part") == "head"), None)
    
    bindings = []
    
    if head_node:
        bindings.append(ParamBinding(
            id="b_scale",
            graph_output_name="scale_augment",
            target_kind=ParamTargetKind.NODE_SCALE_UNIFORM,
            target_id=head_node.id
        ))
        bindings.append(ParamBinding(
            id="b_jump",
            graph_output_name="jump_height",
            target_kind=ParamTargetKind.NODE_POSITION_Y,
            target_id=head_node.id
        ))
        
    # Bind Mood Color to Base Material
    mat_base = next((m for m in scene.materials if m.name == "AndroidAccent"), None)
    if mat_base:
        bindings.append(ParamBinding(
            id="b_color",
            graph_output_name="mood_color",
            target_kind=ParamTargetKind.MATERIAL_COLOR,
            target_id=mat_base.id
        ))
        
    # Bind Camera Distance
    # Ensure camera
    if not scene.camera:
        scene.camera = Camera(
            position=Vector3(x=0, y=1.5, z=5),
            target=Vector3(x=0, y=1, z=0),
            fov=50
        )
    
    bindings.append(ParamBinding(
        id="b_cam",
        graph_output_name="cam_distance",
        target_kind=ParamTargetKind.CAMERA_DISTANCE,
        target_id="camera" 
    ))
    
    # 4. Evaluate & Apply
    inputs = {"energy": energy, "mood": mood, "camera_in_out": camera_in_out}
    results = evaluate_param_graph(graph, inputs)
    scene = apply_param_bindings(scene, results, bindings)
    
    return scene, graph

