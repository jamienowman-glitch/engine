"""Service for Environment Kit & Layout Engine (P0)."""
from __future__ import annotations

import copy
import math
import uuid
from typing import Dict, List, Optional, Tuple

from engines.scene_engine.core.geometry import (
    BoxParams,
    EulerAngles,
    Mesh,
    Transform,
    Vector3,
)
from engines.scene_engine.core.primitives import build_box_mesh
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
    WallSegmentParams,
)
from engines.scene_engine.view.math_utils import (
    add,
    compose_trs,
    cross,
    dot,
    length,
    normalize,
    scale_vec,
    subtract,
)


def _vec3(x, y, z) -> Vector3:
    return Vector3(x=float(x), y=float(y), z=float(z))


def _transform(x=0, y=0, z=0, rx=0, ry=0, rz=0, s=1) -> Transform:
    return Transform(
        position=_vec3(x, y, z),
        rotation=EulerAngles(x=float(rx), y=float(ry), z=float(rz)),
        scale=_vec3(s, s, s)
    )


def _create_env_node(
    name: str,
    kind: EnvPrimitiveKind,
    mesh: Mesh,
    transform: Transform,
    parent_id: Optional[str] = None
) -> SceneNodeV2:
    return SceneNodeV2(
        id=f"env_{uuid.uuid4().hex[:8]}",
        name=name,
        transform=transform,
        mesh_id=mesh.id,
        meta={"env_kind": kind.value}
    )


def build_room(scene: Optional[SceneV2], params: RoomParams) -> Tuple[SceneV2, Dict[str, str]]:
    """Builds a basic parametric room."""
    if scene is None:
        scene = SceneV2(
            id=uuid.uuid4().hex,
            nodes=[],
            meshes=[],
            materials=[],
            # camera=None (optional)
        )
    else:
        scene = copy.deepcopy(scene)
        
    part_map = {}
    new_nodes = []
    new_meshes = []
    
    # 1. Floor
    # Floor is usually centered at (0,0) or (w/2, d/2)?
    # Let's assume params.origin is the center of the floor top surface (y=0).
    # Wait, box primitive is centered.
    # Floor thickness? standard 0.2 probably.
    floor_thick = 0.2
    floor_mesh = build_box_mesh(BoxParams(width=params.width, height=floor_thick, depth=params.depth))
    new_meshes.append(floor_mesh)
    
    floor_pos = params.origin
    # If origin is top surface, box center y is -thickness/2
    floor_center_y = floor_pos.y - (floor_thick / 2.0)
    
    floor_node = _create_env_node(
        "Floor", EnvPrimitiveKind.FLOOR, floor_mesh,
        _transform(x=floor_pos.x, y=floor_center_y, z=floor_pos.z)
    )
    new_nodes.append(floor_node)
    part_map["floor"] = floor_node.id
    
    # 2. Walls
    # 4 walls. N, E, S, W.
    # Assume:
    # Wall North: along +X, at +Z/2 ? Or along X at -Z/2 (front)?
    # Let's align standard conventions:
    # Width is X-axis, Depth is Z-axis.
    # North: +Z direction? Or -Z? 
    # Usually -Z is "forward" in graphics.
    # Let's place walls:
    # Wall 1: Back (-Z edge), X-width.
    # Wall 2: Front (+Z edge), X-width.
    # Wall 3: Left (-X edge), Z-depth.
    # Wall 4: Right (+X edge), Z-depth.
    
    # Needs to handle thickness corner overlap. Simple approach:
    # "Left/Right" walls are full depth.
    # "Front/Back" walls are (width - 2*thickness) to fit between.
    # Or strict miter (hard with boxes).
    # Let's do:
    # N/S walls run full width.
    # E/W walls run (depth - 2*thick).
    
    w_eff = params.width
    d_eff = params.depth - (2 * params.wall_thickness)
    h_eff = params.height
    thick = params.wall_thickness
    
    # North (+Z edge? or -Z?) Let's say +Z is "North" for map logic, but usually -Z is forward.
    # Let's just name them Wall_+Z, Wall_-Z, Wall_+X, Wall_-X.
    
    # Wall +Z (Back)
    mesh_wall_lat = build_box_mesh(BoxParams(width=w_eff, height=h_eff, depth=thick))
    mesh_wall_long = build_box_mesh(BoxParams(width=thick, height=h_eff, depth=d_eff))
    new_meshes.extend([mesh_wall_lat, mesh_wall_long]) # Reusing meshes if possible?
    # Actually unique meshes better for unique texturing/UVs later? 
    # For now reuse geometry if dimensions identical?
    # Let's just create new ones to be safe.
    
    half_h = h_eff / 2.0
    half_d = params.depth / 2.0
    half_w = params.width / 2.0
    
    # Wall +Z
    w_pos_z = half_d - (thick / 2.0)
    node_w_pos_z = _create_env_node(
        "Wall_+Z", EnvPrimitiveKind.WALL_SEGMENT, mesh_wall_lat,
        _transform(x=floor_pos.x, y=floor_pos.y + half_h, z=floor_pos.z + w_pos_z)
    )
    
    # Wall -Z
    w_neg_z = -half_d + (thick / 2.0)
    node_w_neg_z = _create_env_node(
        "Wall_-Z", EnvPrimitiveKind.WALL_SEGMENT, mesh_wall_lat,
        _transform(x=floor_pos.x, y=floor_pos.y + half_h, z=floor_pos.z + w_neg_z)
    )
    
    # Wall +X
    w_pos_x = half_w - (thick / 2.0)
    node_w_pos_x = _create_env_node(
        "Wall_+X", EnvPrimitiveKind.WALL_SEGMENT, mesh_wall_long,
        _transform(x=floor_pos.x + w_pos_x, y=floor_pos.y + half_h, z=floor_pos.z)
    )
    
    # Wall -X
    w_neg_x = -half_w + (thick / 2.0)
    node_w_neg_x = _create_env_node(
        "Wall_-X", EnvPrimitiveKind.WALL_SEGMENT, mesh_wall_long,
        _transform(x=floor_pos.x + w_neg_x, y=floor_pos.y + half_h, z=floor_pos.z)
    )
    
    new_nodes.extend([node_w_pos_z, node_w_neg_z, node_w_pos_x, node_w_neg_x])
    part_map["wall_+z"] = node_w_pos_z.id
    part_map["wall_-z"] = node_w_neg_z.id
    part_map["wall_+x"] = node_w_pos_x.id
    part_map["wall_-x"] = node_w_neg_x.id
    
    # 3. Ceiling
    if params.with_ceiling:
        ceil_mesh = build_box_mesh(BoxParams(width=params.width, height=thick, depth=params.depth))
        new_meshes.append(ceil_mesh)
        ceil_y = params.height + (thick / 2.0)
        ceil_node = _create_env_node(
            "Ceiling", EnvPrimitiveKind.CEILING, ceil_mesh,
            _transform(x=floor_pos.x, y=floor_pos.y + ceil_y, z=floor_pos.z)
        )
        new_nodes.append(ceil_node)
        part_map["ceiling"] = ceil_node.id

    scene.nodes.extend(new_nodes)
    scene.meshes.extend(new_meshes)
    
    if not scene.history:
        scene.history = []
    scene.history.append(ConstructionOp(
        id=f"op_{uuid.uuid4().hex}",
        kind=ConstructionOpKind.CREATE_PRIMITIVE,
        params={"type": "room", "params": params.model_dump()}
    ))
    
    return scene, part_map


def add_wall_segment(scene: SceneV2, params: WallSegmentParams) -> Tuple[SceneV2, str]:
    new_scene = copy.deepcopy(scene)
    
    # Create Mesh (Length along X? Box is W, H, D)
    # We will orient the box along +X, then rotate node to match direction.
    mesh = build_box_mesh(BoxParams(width=params.length, height=params.height, depth=params.thickness))
    new_scene.meshes.append(mesh)
    
    # Orientation
    # Default box is X-aligned (Width).
    # Direction vector d.
    # Angle from X (1,0,0) to d.
    # atan2(dz, dx).
    yaw_rad = math.atan2(params.direction.z, params.direction.x)
    yaw_deg = math.degrees(yaw_rad)
    
    # Box center position
    # Origin is start of wall?
    # Box center X is length/2.
    # Applying rotation:
    # Center World = Origin + (Direction * Length/2) + (Up * Height/2)
    center_offset = scale_vec(normalize(params.direction), params.length / 2.0)
    pos = add(params.origin, center_offset)
    # Adjust Y (origin is bottom?)
    pos.y += params.height / 2.0
    
    node = _create_env_node(
        "WallSegment", EnvPrimitiveKind.WALL_SEGMENT, mesh,
        Transform(
            position=pos,
            rotation=EulerAngles(x=0, y=-yaw_deg, z=0), # Check sign convention. standard math is CCW.
            scale=_vec3(1, 1, 1)
        )
    )
    
    new_scene.nodes.append(node)
    
    return new_scene, node.id


def add_opening_on_wall(
    scene: SceneV2, 
    wall_node_id: str, 
    params: OpeningParams, 
    kind: EnvPrimitiveKind
) -> SceneV2:
    new_scene = copy.deepcopy(scene)
    
    # Find wall node
    # Helper to find node (flat list assumed for now or simple recurse)
    # Reusing find from other modules or implementing simple one
    wall_node = None
    
    def find_node(nodes):
        for n in nodes:
            if n.id == wall_node_id: return n
            f = find_node(n.children)
            if f: return f
        return None
        
    wall_node = find_node(new_scene.nodes)
    if not wall_node:
        raise ValueError(f"Wall node {wall_node_id} not found")
        
    # Create opening volume
    mesh = build_box_mesh(BoxParams(width=params.width, height=params.height, depth=0.3)) # slightly thicker than wall?
    new_scene.meshes.append(mesh)
    
    # Calculate position relative to wall center
    # Wall is length (X local). Origin of wall was... center for Box.
    # BUT `add_wall_segment` calculated center from start origin.
    # The wall node transform IS the center.
    # So local coordinates: 
    # X axis = along wall.
    # -Length/2 is start? Or did we align it?
    # In `add_wall_segment`, node position is Center.
    # So Start is at x = -Length/2 (local).
    # Opening offset is from "wall start".
    # So x_local = (-Length/2) + offset + (OpeningWidth/2).
    
    # We need the wall's length. Not stored in node.
    # We can infer from bound or meta?
    # Mesh bounds? mesh.vertices?
    # box mesh width is stored in PrimitiveParams if available from construction history or just inspecting mesh.
    # Or just assume unit scale and mesh bounds X.
    # `SceneNodeV2` has `mesh_id`.
    mesh_wall = next((m for m in new_scene.meshes if m.id == wall_node.mesh_id), None)
    if not mesh_wall:
         raise ValueError("Wall has no mesh")
         
    # Bounds: Max X - Min X = Length
    # Assuming box centered at 0.
    # If using stored primitives logic:
    wall_len = 1.0
    if mesh_wall.bounds_max and mesh_wall.bounds_min:
        wall_len = mesh_wall.bounds_max.x - mesh_wall.bounds_min.x
    
    start_x = -wall_len / 2.0
    center_x = start_x + params.offset_along_wall + (params.width / 2.0)
    
    # Y pos
    # Wall center Y is Height/2.
    # Start Y (floor) = -Height/2.
    # Sill = distance from floor.
    # Opening center Y = (-Height/2) + Sill + (OpeningHeight/2).
    wall_height = 1.0
    if mesh_wall.bounds_max and mesh_wall.bounds_min:
        wall_height = mesh_wall.bounds_max.y - mesh_wall.bounds_min.y
        
    start_y = -wall_height / 2.0
    center_y = start_y + params.sill_height + (params.height / 2.0)
    
    opening_node = SceneNodeV2(
        id=f"op_{uuid.uuid4().hex[:8]}", # Unique
        name=kind.value,
        transform=_transform(x=center_x, y=center_y, z=0), # Z=0 center of wall thick
        mesh_id=mesh.id,
        meta={"env_kind": kind.value}
    )
    
    wall_node.children.append(opening_node)
    
    return new_scene


def snap_node_to_floor(scene: SceneV2, node_id: str, floor_y: float = 0.0) -> SceneV2:
    new_scene = copy.deepcopy(scene)
    
    # Find Node
    def find_node(nodes):
        for n in nodes:
            if n.id == node_id: return n
            f = find_node(n.children)
            if f: return f
        return None
    target = find_node(new_scene.nodes)
    if not target: return new_scene
    
    # Compute bounds in world space? Or local if logic simple?
    # Assuming scale 1 for P0 simplicity or use mesh bounds * scale.
    bounds_min_y = -0.5 # Default box
    mesh = next((m for m in new_scene.meshes if m.id == target.mesh_id), None)
    if mesh and mesh.bounds_min:
        bounds_min_y = mesh.bounds_min.y * target.transform.scale.y
        
    # Current Bottom Y = NodePos.y + BoundsMinY
    # Desired Bottom Y = floor_y
    # NodePos.y = floor_y - BoundsMinY
    
    target.transform.position.y = floor_y - bounds_min_y
    
    return new_scene


def snap_nodes_to_grid(scene: SceneV2, node_ids: List[str], grid_size: float) -> SceneV2:
    new_scene = copy.deepcopy(scene)
    
    def find_node(nodes, nid):
        for n in nodes:
            if n.id == nid: return n
            f = find_node(n.children, nid)
            if f: return f
        return None
        
    for nid in node_ids:
        node = find_node(new_scene.nodes, nid)
        if node:
            px = node.transform.position.x
            pz = node.transform.position.z
            
            node.transform.position.x = round(px / grid_size) * grid_size
            node.transform.position.z = round(pz / grid_size) * grid_size
            
    return new_scene


def distribute_nodes_along_wall(
    scene: SceneV2, 
    wall_node_id: str, 
    node_ids: List[str], 
    margin: float = 0.5
) -> SceneV2:
    new_scene = copy.deepcopy(scene)
    
    # Find Wall
    def find_node(nodes, nid):
        for n in nodes:
            if n.id == nid: return n
            f = find_node(n.children, nid)
            if f: return f
        return None
        
    wall = find_node(new_scene.nodes, wall_node_id)
    if not wall: return new_scene
    
    # Get Wall Length
    mesh_wall = next((m for m in new_scene.meshes if m.id == wall.mesh_id), None)
    wall_len = 1.0
    if mesh_wall and mesh_wall.bounds_max:
        wall_len = (mesh_wall.bounds_max.x - mesh_wall.bounds_min.x) * wall.transform.scale.x
        
    usable_len = wall_len - (2 * margin)
    if usable_len <= 0: return new_scene
    
    count = len(node_ids)
    if count == 0: return new_scene
    
    # Spacing
    step = usable_len / (count + 1)
    
    start_x = (-wall_len / 2.0) + margin
    
    # For each node:
    # 1. Reparent to wall? Or keep in world and align?
    # Prompt says "distribute... along that wall".
    # Easiest is reparent to wall, set local X.
    # If keeping world, much harder (need wall rotation).
    # Let's reparent for P0 ease, or assume they are already children?
    # The prompt doesn't specify reparenting.
    # But "Align each node’s rotation... toward room center".
    # This implies knowing the wall normal.
    # Wall local normal is usually +Z or -Z (thickness).
    # Let's assume we reparent them to the wall.
    
    for i, nid in enumerate(node_ids):
        node = find_node(new_scene.nodes, nid)
        if not node: continue
        
        # Check if already child? If not, move it?
        # Moving logic requires removing from old parent.
        # Implemented similar logic in Avatar attachment.
        # For simplicity, if it's a root node, remove and add to wall children.
        # If it's somewhere deep, this is risky.
        # Let's assume root nodes for P0 tests.
        if node in new_scene.nodes:
            new_scene.nodes.remove(node)
            wall.children.append(node)
            
        # Set Pos
        lx = start_x + (step * (i + 1))
        # Y? Keep relative or snap? Let's just set X, Z.
        # Z should be "in front" of wall?
        # Wall box center 0. Front face +Depth/2 (or -).
        wall_thick = 0.2
        if mesh_wall and mesh_wall.bounds_max:
            wall_thick = (mesh_wall.bounds_max.z - mesh_wall.bounds_min.z) * wall.transform.scale.z
            
        lz = wall_thick / 2.0 + 0.1 # Slightly in front
        
        node.transform.position.x = lx
        node.transform.position.z = lz # Local Z
        # Y unchanged?
        
        # Orientation: Face away from wall?
        # Wall normal is Z. Node forward is Z?
        # If we want node looking at room center (Away from wall),
        # Node Forward (+Z?) should match Wall Normal (+Z).
        # So rotation 0 relative to wall.
        node.transform.rotation = EulerAngles(x=0, y=0, z=0)
        
    return new_scene
