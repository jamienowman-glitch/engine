"""Tests for Avatar Outfits (P6)."""

from engines.scene_engine.avatar.models import AvatarBodyPart
from engines.scene_engine.avatar.outfits import OutfitItem, wear_outfit
from engines.scene_engine.avatar.service import build_default_avatar
from engines.scene_engine.core.geometry import Transform, Vector3, Quaternion, Mesh, BoxParams
from engines.scene_engine.core.primitives import build_box_mesh
from engines.scene_engine.core.scene_v2 import SceneNodeV2
from engines.scene_engine.view.service import analyze_view
from engines.scene_engine.view.models import ViewAnalysisRequest, ViewportSpec

def test_wear_outfit_masks_nodes():
    scene, rig = build_default_avatar()
    
    # 1. Create a "Shirt" that hides Torso
    mesh = build_box_mesh(BoxParams(width=0.6, height=0.7, depth=0.4))
    shirt_node = SceneNodeV2(
        id="shirt_node",
        name="Shirt",
        transform=Transform(position=Vector3(x=0,y=0,z=0), rotation=Quaternion(x=0,y=0,z=0,w=1), scale=Vector3(x=1,y=1,z=1)),
        mesh_id=mesh.id
    )
    
    item = OutfitItem(
        id="item_shirt",
        name="TShirt",
        nodes=[shirt_node],
        meshes=[mesh],
        materials=[],
        target_body_part=AvatarBodyPart.TORSO,
        mask_body_parts=[AvatarBodyPart.TORSO]
    )
    
    # 2. Wear
    final_scene = wear_outfit(scene, rig, [item])
    
    # 3. Check Torso visibility
    # Find torso node
    torso_bone = next(b for b in rig.bones if b.part == AvatarBodyPart.TORSO)
    def find_node(nodes, nid):
        for n in nodes:
            if n.id == nid: return n
            f = find_node(n.children, nid)
            if f: return f
            
    torso_node = find_node(final_scene.nodes, torso_bone.node_id)
    assert torso_node.meta["visible"] is False
    
    # 4. Check View Engine
    # If visible=False, analyze_view should NOT return it as visible=True
    # Or note: analyze_view returns dict of nodes. P6 implementation of view service skips 'continue'.
    # So it shouldn't appear in results AT ALL, or appear as not found?
    # Logic in service:
    # `_collect_renderbale_nodes` skips.
    # `results` are built from `renderables`.
    # So it won't be in the list.
    
    req = ViewAnalysisRequest(scene=final_scene, viewport=ViewportSpec(screen_width=100, screen_height=100))
    res = analyze_view(req)
    
    found_torso = next((n for n in res.nodes if n.node_id == torso_node.id), None)
    assert found_torso is None # Should be culled

