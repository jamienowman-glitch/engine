"""Outfit System (P6)."""
from __future__ import annotations

from typing import List, Optional

from engines.scene_engine.avatar.kitbash import KitbashPart, assemble_avatar
from engines.scene_engine.avatar.models import AvatarRigDefinition, AvatarBodyPart
from engines.scene_engine.core.scene_v2 import SceneV2

class OutfitItem(KitbashPart):
    mask_body_parts: List[AvatarBodyPart] = []


def wear_outfit(scene: SceneV2, rig: AvatarRigDefinition, items: List[OutfitItem]) -> SceneV2:
    """Applies outfits and masks underlying body parts."""
    
    # 1. Kitbash (add the items)
    # We treat OutfitItems as KitbashParts (inheritance)
    final_scene = assemble_avatar(scene, rig, items)
    
    # 2. Compute Masking
    hidden_parts = set()
    for item in items:
        for part in item.mask_body_parts:
            hidden_parts.add(part)
            
    # 3. Apply Masking (Visibility)
    if not hidden_parts:
        return final_scene
        
    bone_map = {b.part: b.node_id for b in rig.bones}
    
    def find_node(nodes, nid):
        for n in nodes:
            if n.id == nid: return n
            f = find_node(n.children, nid)
            if f: return f
            
    for part in hidden_parts:
        nid = bone_map.get(part)
        if nid:
             node = find_node(final_scene.nodes, nid)
             if node:
                 node.meta["visible"] = False
                 
    return final_scene
