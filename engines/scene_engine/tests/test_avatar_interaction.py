"""Tests for Interaction Engine (P12)."""

from engines.scene_engine.avatar.interaction import interact_stand, interact_grasp, interact_look_at
from engines.scene_engine.avatar.service import build_default_avatar
from engines.scene_engine.avatar.models import AvatarBodyPart
from engines.scene_engine.constraints.models import ConstraintKind
from engines.scene_engine.core.scene_v2 import SceneNodeV2

from engines.scene_engine.core.geometry import Vector3, Transform, EulerAngles

def _default_transform():
    return Transform(
        position=Vector3(x=0, y=0, z=0),
        rotation=EulerAngles(x=0, y=0, z=0),
        scale=Vector3(x=1, y=1, z=1)
    )

def test_interact_stand():
    scene, rig = build_default_avatar()
    
    assert interact_stand(scene, rig)
    
    # Expect 2 constraints (Feet)
    constraints = [c for c in scene.constraints if c.kind == ConstraintKind.KEEP_ON_PLANE]
    assert len(constraints) == 2
    
def test_interact_look_at():
    scene, rig = build_default_avatar()
    
    # Target
    t = SceneNodeV2(id="target_node", transform=_default_transform())
    scene.nodes.append(t)
    
    assert interact_look_at(scene, rig, "target_node")
    
    c = next((c for c in scene.constraints if c.kind == ConstraintKind.AIM_AT_NODE), None)
    assert c is not None
    assert c.target_node_id == "target_node"
    
def test_interact_grasp():
    scene, rig = build_default_avatar()
    
    t = SceneNodeV2(id="cup", transform=_default_transform())
    scene.nodes.append(t)
    
    assert interact_grasp(scene, rig, AvatarBodyPart.HAND_R, "cup")
    
    c = next((c for c in scene.constraints if c.kind == ConstraintKind.ANCHOR_TO_NODE), None)
    assert c is not None
    assert c.target_node_id == "cup"
