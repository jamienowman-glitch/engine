"""Interaction & Contact Engine (P12)."""
from __future__ import annotations

from typing import Optional

from engines.scene_engine.core.scene_v2 import SceneV2, SceneNodeV2
from engines.scene_engine.avatar.models import AvatarRigDefinition, AvatarBodyPart
from engines.scene_engine.constraints.models import SceneConstraint, ConstraintKind

def _find_bone_node(scene: SceneV2, rig: AvatarRigDefinition, part: AvatarBodyPart) -> Optional[str]:
    """Helper to find node ID for a body part."""
    for bone in rig.bones:
        if bone.part == part:
            return bone.node_id
    return None

def interact_grasp(scene: SceneV2, rig: AvatarRigDefinition, hand_part: AvatarBodyPart, target_node_id: str) -> bool:
    """Constraints a hand to a target node (Grasp)."""
    hand_node_id = _find_bone_node(scene, rig, hand_part)
    if not hand_node_id:
        return False
        
    c = SceneConstraint(
        id=f"grasp_{hand_part.value}",
        kind=ConstraintKind.ANCHOR_TO_NODE,
        node_id=hand_node_id,
        target_node_id=target_node_id
    )
    scene.constraints.append(c)
    return True

def interact_look_at(scene: SceneV2, rig: AvatarRigDefinition, target_node_id: str) -> bool:
    """Constraints head to look at a target."""
    head_node_id = _find_bone_node(scene, rig, AvatarBodyPart.HEAD)
    if not head_node_id:
        return False
        
    c = SceneConstraint(
        id="look_at_target",
        kind=ConstraintKind.AIM_AT_NODE,
        node_id=head_node_id,
        target_node_id=target_node_id
    )
    scene.constraints.append(c)
    return True

def interact_stand(scene: SceneV2, rig: AvatarRigDefinition, floor_y: float = 0.0) -> bool:
    """Constraints feet to floor plane."""
    # Find feet
    foot_l = _find_bone_node(scene, rig, AvatarBodyPart.FOOT_L)
    foot_r = _find_bone_node(scene, rig, AvatarBodyPart.FOOT_R)
    
    if not foot_l or not foot_r:
        return False
        
    c_l = SceneConstraint(
        id="stand_l",
        kind=ConstraintKind.KEEP_ON_PLANE,
        node_id=foot_l,
        plane_offset=floor_y
    )
    c_r = SceneConstraint(
        id="stand_r",
        kind=ConstraintKind.KEEP_ON_PLANE,
        node_id=foot_r,
        plane_offset=floor_y
    )
    scene.constraints.append(c_l)
    scene.constraints.append(c_r)
    return True
