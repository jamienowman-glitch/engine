
import pytest
import uuid
import math
from engines.scene_engine.core.scene_v2 import SceneV2, SceneNodeV2
from engines.scene_engine.core.geometry import Transform, Vector3, EulerAngles
from engines.scene_engine.constraints.models import SceneConstraint, ConstraintKind
from engines.scene_engine.constraints.service import solve_constraints

def _create_simple_scene():
    return SceneV2(id="test_scene", nodes=[])

def _create_node(id, x, y, z):
    return SceneNodeV2(
        id=id,
        transform=Transform(
            position=Vector3(x=x, y=y, z=z),
            rotation=EulerAngles(x=0, y=0, z=0),
            scale=Vector3(x=1, y=1, z=1)
        )
    )

def test_keep_on_plane():
    scene = _create_simple_scene()
    # Node at y=5
    node = _create_node("n1", 0, 5, 0)
    scene.nodes.append(node)
    
    # Constraint y=0
    c = SceneConstraint(
        id="c1",
        kind=ConstraintKind.KEEP_ON_PLANE,
        node_id="n1",
        plane_normal=Vector3(x=0, y=1, z=0),
        plane_offset=0
    )
    scene.constraints.append(c)
    
    solved = solve_constraints(scene)
    
    s_node = solved.nodes[0]
    assert abs(s_node.transform.position.y) < 1e-3
    assert abs(s_node.transform.position.x - 0) < 1e-3 # Should maintain X

def test_maintain_distance():
    scene = _create_simple_scene()
    n1 = _create_node("n1", 0, 0, 0)
    n2 = _create_node("n2", 2, 0, 0) # Dist 2
    scene.nodes.extend([n1, n2])
    
    # Constrain n2 to be 5 units from n1
    c = SceneConstraint(
        id="c1",
        kind=ConstraintKind.MAINTAIN_DISTANCE,
        node_id="n2",
        target_node_id="n1",
        distance=5.0
    )
    scene.constraints.append(c)
    
    solved = solve_constraints(scene)
    s_n2 = next(n for n in solved.nodes if n.id == "n2")
    
    # Should move along X axis to x=5 or x=-5? 
    # Logic moves along line, so x=5.
    assert abs(s_n2.transform.position.x - 5.0) < 1e-3

def test_aim_at_node():
    scene = _create_simple_scene()
    eye = _create_node("eye", 0, 0, 0)
    # Target at (1, 0, 1) -> 45 degrees yaw (approx 0.78 rad)
    target = _create_node("target", 1, 0, 1)
    scene.nodes.extend([eye, target])
    
    c = SceneConstraint(
        id="c1",
        kind=ConstraintKind.AIM_AT_NODE,
        node_id="eye",
        target_node_id="target"
    )
    scene.constraints.append(c)
    
    solved = solve_constraints(scene)
    s_eye = next(n for n in solved.nodes if n.id == "eye")
    
    yaw = s_eye.transform.rotation.y
    # Target (1,0,1)
    # Atan2(1,1) = pi/4 = 0.785
    assert abs(yaw - 0.785) < 0.1
