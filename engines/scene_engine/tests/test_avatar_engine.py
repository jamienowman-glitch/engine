"""Tests for Avatar Rig & Attachment Engine (P0)."""
from engines.scene_engine.avatar.models import AvatarAttachmentSlot, AvatarBodyPart
from engines.scene_engine.avatar.service import (
    apply_avatar_pose,
    attach_node_to_avatar_slot,
    build_default_avatar,
    insert_default_avatar_into_scene,
)
from engines.scene_engine.core.geometry import EulerAngles, Transform, Vector3
from engines.scene_engine.core.scene_v2 import SceneNodeV2, SceneV2
from engines.scene_engine.core.types import Camera


def test_build_default_avatar():
    scene, rig = build_default_avatar()
    
    assert len(scene.nodes) > 0
    assert len(scene.meshes) > 0
    assert len(rig.bones) > 10
    
    # Check for Head bone
    head_bone = next((b for b in rig.bones if b.part == AvatarBodyPart.HEAD), None)
    assert head_bone is not None
    
    # Check node existence
    head_node = next((n for n in scene.nodes[0].children[0].children if n.id == head_bone.node_id), None) 
    # Hierarchy traversal is hard to assert path blindly, let's just search recursive if needed or trust list extension
    # Actually I can recurse search simply
    def find_node(nodes, nid):
        for n in nodes:
            if n.id == nid: return n
            found = find_node(n.children, nid)
            if found: return found
        return None
        
    found_head = find_node(scene.nodes, head_bone.node_id)
    assert found_head is not None
    assert found_head.name == "Head"


def test_insert_into_scene():
    base_scene = SceneV2(id="base", nodes=[], meshes=[], materials=[])
    updated_scene, rig = insert_default_avatar_into_scene(base_scene)
    
    assert len(updated_scene.nodes) > len(base_scene.nodes)
    assert len(updated_scene.meshes) > len(base_scene.meshes)
    assert rig.root_bone_id is not None


def test_apply_pose():
    scene, rig = build_default_avatar()
    
    # Pose: Rotate Head
    new_transform = Transform(
        position=Vector3(x=0, y=0.15, z=0),
        rotation=EulerAngles(x=0, y=90, z=0), # Turn head
        scale=Vector3(x=1, y=1, z=1)
    )
    
    posed_scene = apply_avatar_pose(
        scene, rig, 
        {AvatarBodyPart.HEAD: new_transform}
    )
    
    # Verify
    head_bone = next(b for b in rig.bones if b.part == AvatarBodyPart.HEAD)
    
    def find_node(nodes, nid):
        for n in nodes:
            if n.id == nid: return n
            found = find_node(n.children, nid)
            if found: return found
        return None
        
    head_node = find_node(posed_scene.nodes, head_bone.node_id)
    assert head_node.transform.rotation.y == 90.0


def test_attach_prop():
    scene, rig = build_default_avatar()
    
    # Create a Prop Node at root
    prop_id = "my_hat"
    prop_node = SceneNodeV2(
        id=prop_id, 
        name="Hat", 
        transform=Transform(
            position=Vector3(x=10, y=10, z=10), # Far away
            rotation=EulerAngles(x=0, y=0, z=0),
            scale=Vector3(x=1, y=1, z=1)
        )
    )
    scene.nodes.append(prop_node)
    
    # Attach to Head Top
    updated_scene = attach_node_to_avatar_slot(
        scene, rig, AvatarAttachmentSlot.HEAD_TOP, prop_id
    )
    
    # Verify hierarchy: Prop should not be in root nodes anymore
    assert len([n for n in updated_scene.nodes if n.id == prop_id]) == 0
    
    # Verify parentage: Should be child of Head
    head_bone = next(b for b in rig.bones if b.part == AvatarBodyPart.HEAD)
    
    def find_node_with_children(nodes, nid):
        for n in nodes:
            if n.id == nid: return n
            found = find_node_with_children(n.children, nid)
            if found: return found
        return None

    head_node = find_node_with_children(updated_scene.nodes, head_bone.node_id)
    assert head_node is not None
    
    child_ids = [c.id for c in head_node.children]
    assert prop_id in child_ids
    
    # Verify transform snap (y=0.25 from default avatar head top attachment)
    attached_prop = next(c for c in head_node.children if c.id == prop_id)
    assert attached_prop.transform.position.y == 0.25
