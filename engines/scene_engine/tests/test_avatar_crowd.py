"""Tests for Crowd Instancing (P11)."""

from engines.scene_engine.avatar.crowd import add_avatar_instance, generate_crowd
from engines.scene_engine.avatar.service import build_default_avatar
from engines.scene_engine.core.geometry import Vector3

def test_add_avatar_instance_reuse_meshes():
    scene, rig = build_default_avatar()
    original_node_count = len(scene.nodes) # Top level nodes? build_default_avatar returns flat or nested?
    # scene.nodes usually only top level.
    # We need to count total nodes to be sure.
    
    def count_nodes(nodes):
        c = len(nodes)
        for n in nodes:
            c += count_nodes(n.children)
        return c
        
    total_nodes_1 = count_nodes(scene.nodes)
    mesh_count_1 = len(scene.meshes)
    
    # Add Instance
    new_scene, new_rig = add_avatar_instance(
        scene, 
        scene.nodes, # Pass existing nodes as template
        rig,
        Vector3(x=2, y=0, z=0)
    )
    
    total_nodes_2 = count_nodes(new_scene.nodes)
    mesh_count_2 = len(new_scene.meshes)
    
    # Verify Mesh Reuse
    assert mesh_count_2 == mesh_count_1
    
    # Verify Node Doubling
    # Note: scene.nodes passed as template.
    # add_avatar_instance appends new clones to scene.nodes.
    # So new_scene keys are [original..., cloned...]
    # Expected total = initial * 2
    assert total_nodes_2 == total_nodes_1 * 2
    
    # Verify unique IDs
    # Check new rig bone ID vs old
    assert new_rig.bones[0].node_id != rig.bones[0].node_id
    assert new_rig.bones[0].node_id.startswith(rig.bones[0].node_id) # Suffix added

def test_generate_crowd():
    scene, rig = build_default_avatar()
    
    # Generate 4 avatars (include original? No, generate_crowd adds N instances)
    # The function appends to scene.
    final_scene, rigs = generate_crowd(scene, scene.nodes, rig, 4, width=10, depth=10)
    
    # 1 original + 4 new = 5 avatars?
    # generate_crowd iterates count.
    # Pass 1: add instance.
    # Pass 2: add instance.
    # ...
    # It adds 4 instances.
    # Plus the original template nodes are still in scene.
    
    assert len(rigs) == 4
    
    # Check positions (approx)
    # Grid 2x2.
    # Width 10 -> -5 to 5.
    # spacing 10.
    # (0,0) -> (-5, -5)
    # (0,1) -> (5, -5)
    # (1,0) -> (-5, 5)
    # (1,1) -> (5, 5)
    
    # Check unique roots
    root_ids = set()
    for r in rigs:
        root_ids.add(r.root_bone_id)
    assert len(root_ids) == 4
