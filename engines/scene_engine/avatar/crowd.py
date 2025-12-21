"""Crowd Instancing Engine (P11)."""
from __future__ import annotations

import copy
import uuid
from typing import List, Tuple, Dict, Optional

from engines.scene_engine.core.scene_v2 import SceneV2, SceneNodeV2
from engines.scene_engine.core.geometry import Vector3, EulerAngles
from engines.scene_engine.avatar.models import AvatarRigDefinition, AvatarBone

def _generate_id_map(nodes: List[SceneNodeV2], suffix: str) -> Dict[str, str]:
    """Generates a map of old_id -> new_id with suffix."""
    id_map = {}
    
    def traverse(n_list):
        for n in n_list:
            new_id = f"{n.id}_{suffix}"
            id_map[n.id] = new_id
            traverse(n.children)
            
    traverse(nodes)
    return id_map

def _clone_and_rename_nodes(nodes: List[SceneNodeV2], id_map: Dict[str, str]) -> List[SceneNodeV2]:
    """Deep copies nodes and updates IDs based on map."""
    
    def recurse(n_in: SceneNodeV2) -> SceneNodeV2:
        n_out = copy.deepcopy(n_in)
        n_out.id = id_map[n_in.id]
        if n_out.name: n_out.name = f"{n_out.name}_{id_map[n_in.id].split('_')[-1]}"
        
        # Update children
        new_children = []
        for child in n_in.children:
            new_children.append(recurse(child))
        n_out.children = new_children
        
        return n_out
        
    result = []
    for n in nodes:
        result.append(recurse(n))
    return result

def add_avatar_instance(
    scene: SceneV2, 
    template_nodes: List[SceneNodeV2], # Usually just [root_node]
    template_rig: AvatarRigDefinition,
    position: Vector3,
    rotation_y_deg: float = 0.0
) -> Tuple[SceneV2, AvatarRigDefinition]:
    """Adds a new instance of the avatar to the scene, reusing meshes."""
    
    instance_id = uuid.uuid4().hex[:6]
    
    # 1. Map IDs
    id_map = _generate_id_map(template_nodes, instance_id)
    
    # 2. Clone Nodes
    new_nodes = _clone_and_rename_nodes(template_nodes, id_map)
    
    # 3. Position Root(s)
    # Be careful if multiple roots. Usually avatar has 1 root (Pelvis or separate Root).
    # We apply transform to all top-level nodes of the template.
    for node in new_nodes:
        # If node has existing transform, we compose or overwrite?
        # Usually avatars are built at origin.
        # We add the instance position.
        node.transform.position.x += position.x
        node.transform.position.y += position.y
        node.transform.position.z += position.z
        
        # Rotation (Y-axis)
        # Simple Euler addition for P0
        if isinstance(node.transform.rotation, EulerAngles):
             node.transform.rotation.y += rotation_y_deg
             
    # 4. Create New Rig Def
    new_bones = []
    for bone in template_rig.bones:
        new_node_id = id_map.get(bone.node_id)
        if new_node_id:
            new_bones.append(AvatarBone(
                id=f"{bone.id}_{instance_id}",
                node_id=new_node_id,
                part=bone.part,
                parent_id=f"{bone.parent_id}_{instance_id}" if bone.parent_id else None
            ))
            
    new_root_id = f"{template_rig.root_bone_id}_{instance_id}"
    
    # 4b. Remap Attachments
    new_attachments = []
    for att in template_rig.attachments:
        new_attachments.append(copy.deepcopy(att))
        new_attachments[-1].bone_id = f"{att.bone_id}_{instance_id}"
    
    new_rig = AvatarRigDefinition(
        root_bone_id=new_root_id if new_root_id else template_rig.root_bone_id,
        bones=new_bones,
        attachments=new_attachments
    )
    
    # 5. Add to Scene
    # Note: We do NOT add meshes/materials to scene because we assume they are already there 
    # (if reusing from existing scene content) OR we need to ensure they exist.
    # If 'template_nodes' came from 'scene', meshes exist.
    # If they came from a library scene, we might need to merge meshes.
    # Logic: `replace_file_content` logic assumes we work on same scene or merged?
    # Function signature: `scene` is the target.
    # We append `new_nodes` to `scene.nodes`.
    scene.nodes.extend(new_nodes)
    
    return scene, new_rig

def generate_crowd(
    scene: SceneV2,
    template_nodes: List[SceneNodeV2],
    template_rig: AvatarRigDefinition,
    count: int,
    width: float = 10.0,
    depth: float = 10.0
) -> Tuple[SceneV2, List[AvatarRigDefinition]]:
    """Generates a grid/crowd of avatars."""
    
    rigs = []
    
    import math
    cols = int(math.sqrt(count))
    if cols == 0: cols = 1
    rows = math.ceil(count / cols)
    
    spacing_x = width / max(1, cols-1) if cols > 1 else 0
    spacing_z = depth / max(1, rows-1) if rows > 1 else 0
    
    start_x = -width / 2.0
    start_z = -depth / 2.0
    
    current_scene = scene
    
    for i in range(count):
        row = i // cols
        col = i % cols
        
        pos = Vector3(
            x=start_x + (col * spacing_x),
            y=0.0,
            z=start_z + (row * spacing_z)
        )
        
        current_scene, new_rig = add_avatar_instance(
            current_scene,
            template_nodes,
            template_rig,
            pos,
            rotation_y_deg=0.0
        )
        rigs.append(new_rig)
        
    return current_scene, rigs
