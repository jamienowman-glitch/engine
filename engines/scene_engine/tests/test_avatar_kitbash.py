"""Tests for Avatar Kitbashing & Export (P5)."""

import json
from engines.scene_engine.avatar.kitbash import KitbashPart, assemble_avatar
from engines.scene_engine.avatar.models import AvatarBodyPart
from engines.scene_engine.avatar.service import build_default_avatar
from engines.scene_engine.core.geometry import Transform, Vector3, Quaternion, Mesh, BoxParams
from engines.scene_engine.core.scene_v2 import SceneNodeV2, Material
from engines.scene_engine.core.primitives import build_box_mesh

from engines.scene_engine.export.service import export_scene, ExportFormat

def test_kitbash_attaches_part():
    # 1. Base Avatar
    scene, rig = build_default_avatar()
    
    # 2. Create Hat Part
    mesh = build_box_mesh(BoxParams(width=0.2, height=0.1, depth=0.2))
    hat_node = SceneNodeV2(
        id="hat_root",
        name="HatRoot",
        transform=Transform(
            position=Vector3(x=0,y=0,z=0),
            rotation=Quaternion(x=0,y=0,z=0,w=1),
            scale=Vector3(x=1,y=1,z=1)
        ),
        mesh_id=mesh.id
    )
    
    part = KitbashPart(
        id="part_hat",
        name="TopHat",
        nodes=[hat_node],
        meshes=[mesh],
        materials=[],
        target_body_part=AvatarBodyPart.HEAD,
        local_offset=Transform(
            position=Vector3(x=0, y=0.15, z=0), # Sit above head
            rotation=Quaternion(x=0,y=0,z=0,w=1),
            scale=Vector3(x=1,y=1,z=1)
        )
    )
    
    # 3. Assemble
    new_scene = assemble_avatar(scene, rig, [part])
    
    # 4. Verify
    # Find Head node (should verify checking children)
    # Recursively find head
    # The default avatar build uses "Head" name or look up via rig
    head_bone = next(b for b in rig.bones if b.part == AvatarBodyPart.HEAD)
    
    def find_node(nodes, nid):
        for n in nodes:
            if n.id == nid: return n
            f = find_node(n.children, nid)
            if f: return f
    
    head_node = find_node(new_scene.nodes, head_bone.node_id)
    assert head_node is not None
    
    # Check if Hat is child
    hat = next((c for c in head_node.children if c.name == "TopHat:HatRoot" or c.id == "hat_root"), None)
    # The kitbash logic copies the node.
    assert hat is not None
    assert hat.transform.position.y == 0.15


def test_export_gltf_structure():
    scene, rig = build_default_avatar()
    data = export_scene(scene, ExportFormat.GLTF_JSON)
    
    assert "asset" in data
    assert data["asset"]["version"] == "2.0"
    assert len(data["nodes"]) >= len(scene.nodes) # Flattened list
    assert len(data["meshes"]) > 0
