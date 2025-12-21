"""Kitbashing Engine (P5).

Allows assembling avatars from multiple parts/assets.
"""
from __future__ import annotations

import copy
import uuid
from typing import List, Optional

from pydantic import BaseModel

from engines.scene_engine.avatar.models import AvatarRigDefinition, AvatarBodyPart
from engines.scene_engine.core.scene_v2 import SceneV2, SceneNodeV2, Mesh, Material
from engines.scene_engine.core.geometry import Transform, Vector3, Quaternion

class KitbashPart(BaseModel):
    id: str
    name: str
    
    # The geometry
    nodes: List[SceneNodeV2]
    meshes: List[Mesh]
    materials: List[Material]
    
    # Binding
    target_body_part: Optional[AvatarBodyPart] = None
    # If None, attached to Root or just floating? Usually we want to Attach.
    
    local_offset: Optional[Transform] = None


def assemble_avatar(
    base_scene: SceneV2, 
    base_rig: AvatarRigDefinition, 
    parts: List[KitbashPart]
) -> SceneV2:
    """Merges parts into the base avatar scene."""
    new_scene = copy.deepcopy(base_scene)
    
    # Build bone node map
    bone_map = {b.part: b.node_id for b in base_rig.bones}
    
    # Node lookup for attachment
    def find_node(nodes, nid):
        for n in nodes:
            if n.id == nid: return n
            f = find_node(n.children, nid)
            if f: return f
        return None
        
    for part in parts:
        # 1. Merge Assets
        new_scene.meshes.extend(part.meshes)
        new_scene.materials.extend(part.materials)
        
        # 2. Attach Nodes
        # If target_body_part is set, we find the bone node and parent the PART ROOTs to it.
        # If not, we parent to scene root.
        
        target_node_id = None
        if part.target_body_part:
            target_node_id = bone_map.get(part.target_body_part)
            
        target_parent = None
        if target_node_id:
            target_parent = find_node(new_scene.nodes, target_node_id)
        
        # If no target parent found (or not specified), fallback to scene root list?
        # Or error? For Kitbashing, usually we want to attach to something. 
        # Fallback: append to top-level.
        
        for node in part.nodes:
            # Clone node to be safe? (Input part might be reused)
            p_node = copy.deepcopy(node)
            
            # Apply offset if root
            if part.local_offset:
                # Merge transform? Or replace?
                # Usually offset is "relative to mount point".
                # Logic: p_node.transform = part.local_offset
                # (Assuming part nodes are local to the part origin)
                p_node.transform = part.local_offset
            
            if target_parent:
                target_parent.children.append(p_node)
            else:
                new_scene.nodes.append(p_node)
                
    return new_scene
