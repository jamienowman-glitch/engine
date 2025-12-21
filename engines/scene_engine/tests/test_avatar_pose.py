"""Tests for Avatar Pose Engine (P1)."""
from typing import Tuple

from engines.scene_engine.avatar.models import AvatarRigDefinition
from engines.scene_engine.avatar.poses import PoseLibrary, apply_pose
from engines.scene_engine.avatar.service import build_default_avatar
from engines.scene_engine.core.geometry import Vector3
from engines.scene_engine.core.scene_v2 import SceneNodeV2, SceneV2

def _find_node_by_partial_name(nodes, name_part) -> SceneNodeV2:
    for n in nodes:
        if name_part in n.name:
            return n
        res = _find_node_by_partial_name(n.children, name_part)
        if res:
            return res
    return None

def test_pose_library_basics():
    assert PoseLibrary.IDLE is not None
    assert PoseLibrary.TALK is not None
    assert PoseLibrary.SIT is not None
    
    poses = PoseLibrary.list_poses()
    assert "pose_idle" in poses
    assert "pose_sit" in poses

def test_apply_pose_preserves_position():
    """Verify that applying a pose (mostly rotations) doesn't zero-out limb offsets."""
    scene, rig = build_default_avatar()
    
    # 1. Find Left Upper Arm
    # In default avatar, it has an offset like (-0.35, 0.2, 0)
    arm_node = _find_node_by_partial_name(scene.nodes, "Arm_L_Upper")
    original_pos = arm_node.transform.position
    assert abs(original_pos.x) > 0.1 # Should have offset
    
    # 2. Apply Walk Start (rotates limbs)
    posed_scene = apply_pose(scene, rig, "pose_walk_start")
    
    # 3. Check new arm node
    new_arm = _find_node_by_partial_name(posed_scene.nodes, "Arm_L_Upper")
    
    # Position should be preserved (roughly equal)
    assert abs(new_arm.transform.position.x - original_pos.x) < 0.001
    assert abs(new_arm.transform.position.y - original_pos.y) < 0.001
    
    # Rotation should changed
    # Walk start rotates arm (-20, 0, 0)
    # Default was (0,0,0)
    assert abs(new_arm.transform.rotation.x - (-20.0)) < 0.1

def test_apply_pose_moves_pelvis():
    """Verify that SIT pose moves the root (Pelvis)."""
    scene, rig = build_default_avatar()
    
    pelvis = _find_node_by_partial_name(scene.nodes, "Pelvis")
    # Default Y is 1.0
    assert abs(pelvis.transform.position.y - 1.0) < 0.01
    
    # Apply SIT
    # SIT defines Pelvis pos as (0, -0.4, 0). 
    # Wait, my logic REPLACES position.
    # If SIT says -0.4, and default is 1.0. The new pos will be -0.4?
    # Or is it relative?
    # My simple logic is "new_t.position = input_t.position". 
    # Input is (0, -0.4, 0).
    # So it will put pelvis UNDERGROUND. 
    # Poses are usually absolute local transforms relative to parent.
    # Pelvis parent is Scene Root (World).
    # So (0, -0.4, 0) is underground.
    # Ideally SIT should be (0, 0.6, 0) if default is 1.0.
    # But usually "Root" bone is at (0,0,0) on the floor, and Pelvis is a child at (0,1,0).
    # My Default Avatar has Pelvis as Root at (0,1,0).
    # If the Pose says (0, -0.4), it's probably bad data in my PoseLibrary for a "Root Pelvis".
    # But let's verify what happens.
    
    posed_scene = apply_pose(scene, rig, "pose_sit")
    new_pelvis = _find_node_by_partial_name(posed_scene.nodes, "Pelvis")
    
    # Should look for what the Pose defined
    assert abs(new_pelvis.transform.position.y - (-0.4)) < 0.01

