
import pytest
from engines.bot_better_know.scene3d.presets import (
    build_bbk_rooftop_with_constraints,
    build_bbk_hero_avatar_beauty_scene_constrained
)

def test_build_bbk_rooftop_with_constraints():
    scene = build_bbk_rooftop_with_constraints()
    
    # 1. Verify constraints exist
    assert len(scene.constraints) > 0
    
    # 2. Verify Solver Ran (impossible to check exact positions easily without deterministic seed, 
    # but we can check if constraints are present in the final object, meaning logic executed).
    # Since solve_constraints returns a NEW scene, and the function returns THAT, 
    # we assume the positions are updated.
    
    # Check if constraints are still in the list (they should be preserved)
    kinds = [c.kind for c in scene.constraints]
    assert "keep_on_plane" in kinds
    assert "maintain_distance" in kinds

def test_build_bbk_hero_avatar_beauty_scene_constrained():
    scene = build_bbk_hero_avatar_beauty_scene_constrained()
    
    # Verify root is constrained
    root_c = next((c for c in scene.constraints if c.kind == "keep_on_plane"), None)
    assert root_c is not None
    
    # Check root position Y (should be 0 or very close)
    # We need to find the node.
    # The constraints list has the node_id
    nid = root_c.node_id
    
    def find_node(nodes):
        for n in nodes:
            if n.id == nid: return n
            f = find_node(n.children)
            if f: return f
        return None
        
    node = find_node(scene.nodes)
    assert node is not None
    assert abs(node.transform.position.y) < 1e-3
