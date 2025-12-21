"""Tests for Avatar Variation (P10)."""

from engines.scene_engine.avatar.variation import randomize_avatar
from engines.scene_engine.avatar.service import build_default_avatar
from engines.scene_engine.core.geometry import Vector3

def test_randomize_avatar_determinism():
    scene, rig = build_default_avatar()
    
    # Run 1: Seed "A"
    s1 = randomize_avatar(scene, rig, "A")
    # Run 2: Seed "A"
    s2 = randomize_avatar(scene, rig, "A")
    # Run 3: Seed "B"
    s3 = randomize_avatar(scene, rig, "B")
    
    # Verify s1 == s2 (transforms at least)
    # Check Pelvis scale/pos or Head pos (Height affects head pos)
    
    # Helper to find Head
    head_bone = next(b for b in rig.bones if "head" in b.node_id.lower() or "head" in b.part.value.lower())
    
    def find_node(nodes, nid):
        for n in nodes:
            if n.id == nid: return n
            f = find_node(n.children, nid)
            if f: return f
            
    head1 = find_node(s1.nodes, head_bone.node_id)
    head2 = find_node(s2.nodes, head_bone.node_id)
    head3 = find_node(s3.nodes, head_bone.node_id)
    
    # Determinism
    # Transforms should be identical
    # compare meta height or scale
    
    # Find Pelvis (Root)
    pelvis_bone = next(b for b in rig.bones if b.id == rig.root_bone_id)
    pelvis1 = find_node(s1.nodes, pelvis_bone.node_id)
    pelvis2 = find_node(s2.nodes, pelvis_bone.node_id)
    pelvis3 = find_node(s3.nodes, pelvis_bone.node_id)
    
    # Scale Y should be identical for same seed
    assert abs(pelvis1.transform.scale.y - pelvis2.transform.scale.y) < 0.0001
    
    # Variation
    # Seed A vs B should differ in height/scale
    assert abs(pelvis1.transform.scale.y - pelvis3.transform.scale.y) > 0.001

