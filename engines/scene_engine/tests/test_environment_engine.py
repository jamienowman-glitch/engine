"""Tests for Environment Kit & Layout Engine (P0)."""
from engines.scene_engine.core.geometry import EulerAngles, Transform, Vector3
from engines.scene_engine.core.scene_v2 import SceneNodeV2, SceneV2
from engines.scene_engine.core.types import Camera
from engines.scene_engine.environment.models import (
    EnvPrimitiveKind,
    OpeningParams,
    RoomParams,
    WallSegmentParams,
)
from engines.scene_engine.environment.service import (
    add_opening_on_wall,
    add_wall_segment,
    build_room,
    distribute_nodes_along_wall,
    snap_node_to_floor,
    snap_nodes_to_grid,
)


def test_build_room():
    params = RoomParams(width=10, depth=10, height=3)
    scene, parts = build_room(None, params)
    
    assert len(scene.nodes) >= 5 # Floor + 4 Walls (Ceiling optional default true)
    assert "floor" in parts
    assert "wall_+z" in parts
    
    # Check floor
    floor = next(n for n in scene.nodes if n.id == parts["floor"])
    assert floor.meta["env_kind"] == EnvPrimitiveKind.FLOOR.value
    
    # Check dimensions roughly
    # Wall +Z pos
    w_z = next(n for n in scene.nodes if n.id == parts["wall_+z"])
    # Depth 10. Origin 0. Wall center z roughly 5 (minus thick)
    assert w_z.transform.position.z > 4.0


def test_add_wall_segment():
    base_scene = SceneV2(id="base", nodes=[], meshes=[], materials=[])
    
    params = WallSegmentParams(
        length=5, height=3, thickness=0.2,
        origin=Vector3(x=0, y=0, z=0),
        direction=Vector3(x=1, y=0, z=0) # Along +X
    )
    
    updated, new_id = add_wall_segment(base_scene, params)
    
    assert len(updated.nodes) == 1
    node = updated.nodes[0]
    assert node.id == new_id
    
    # Center should be at (2.5, 1.5, 0)
    assert node.transform.position.x == 2.5
    assert node.transform.position.y == 1.5


def test_add_opening_on_wall():
    # Build a wall manually or use builder
    base_scene = SceneV2(id="base", nodes=[], meshes=[], materials=[])
    params = WallSegmentParams(
        length=4.0, height=3.0, thickness=0.2,
        origin=Vector3(x=0, y=0, z=0),
        direction=Vector3(x=1, y=0, z=0)
    )
    scene, wall_id = add_wall_segment(base_scene, params)
    
    opening_p = OpeningParams(
        width=1.0, height=2.0, 
        sill_height=0.0, 
        offset_along_wall=1.0 # 1m from start
    )
    
    scene = add_opening_on_wall(
        scene, wall_id, opening_p, EnvPrimitiveKind.DOOR_OPENING
    )
    
    wall = scene.nodes[0]
    assert len(wall.children) == 1
    op = wall.children[0]
    assert op.meta["env_kind"] == EnvPrimitiveKind.DOOR_OPENING.value
    
    # X local check
    # Length 4. Start X = -2.
    # Offset 1. Width 1 (Center +0.5).
    # Expected X = -2 + 1 + 0.5 = -0.5
    assert abs(op.transform.position.x - (-0.5)) < 0.01


def test_snap_to_floor():
    node = SceneNodeV2(
        id="prop", 
        name="Prop", 
        transform=Transform(position=Vector3(x=0, y=10, z=0), rotation=EulerAngles(x=0,y=0,z=0), scale=Vector3(x=1,y=1,z=1))
    )
    # No mesh bounds? logic fallback to -0.5
    # Let's mock a mesh w bounds if needed or assume default
    # If no mesh, `snap_node_to_floor` assumes Box bounds -0.5
    
    scene = SceneV2(id="s", nodes=[node], meshes=[], materials=[])
    
    snapped = snap_node_to_floor(scene, "prop", floor_y=0.0)
    
    # Default box min y -0.5
    # Target Bottom = 0.
    # Center = 0.5
    assert snapped.nodes[0].transform.position.y == 0.5


def test_distribute_along_wall():
    # Wall length 10
    wall_params = WallSegmentParams(
        length=10, height=3, thickness=0.2,
        origin=Vector3(x=0,y=0,z=0), direction=Vector3(x=1,y=0,z=0)
    )
    scene, wall_id = add_wall_segment(
        SceneV2(id="b", nodes=[], meshes=[], materials=[]),
        wall_params
    )
    
    # 3 props
    props = []
    for i in range(3):
        p = SceneNodeV2(
            id=f"p{i}", name=f"p{i}",
            transform=Transform(position=Vector3(x=0,y=0,z=0), rotation=EulerAngles(x=0,y=0,z=0), scale=Vector3(x=1,y=1,z=1))
        )
        props.append(p)
        scene.nodes.append(p)
        
    p_ids = [n.id for n in props]
    
    scene = distribute_nodes_along_wall(scene, wall_id, p_ids, margin=1.0)
    
    # Assert props moved to children of wall
    wall = next(n for n in scene.nodes if n.id == wall_id)
    assert len(wall.children) == 3
    
    # Check X spacing
    # Length 10. Margin 1. Usable 8.
    # 3 items. 4 spans. Steps = 2.
    # Start X = -5 + 1 = -4.
    # P0: -4 + 2 = -2
    # P1: -4 + 4 = 0
    # P2: -4 + 6 = 2
    
    xs = sorted([c.transform.position.x for c in wall.children])
    assert abs(xs[0] - (-2.0)) < 0.1
    assert abs(xs[1] - 0.0) < 0.1
    assert abs(xs[2] - 2.0) < 0.1
