"""Instancing Utilities."""
from __future__ import annotations

import uuid
from engines.scene_engine.core.scene_v2 import SceneV2, SceneNodeV2
from engines.scene_engine.core.geometry import Transform, Vector3, EulerAngles

def create_instance(
    scene: SceneV2, 
    prototype_node_id: str, 
    position: Vector3
) -> str:
    """
    Creates a new Node that shares mesh/material of prototype.
    Returns new node ID.
    """
    # Find prototype
    proto = None
    
    def find(nodes):
        nonlocal proto
        if proto: return
        for n in nodes:
            if n.id == prototype_node_id:
                proto = n
                return
            find(n.children)
            
    find(scene.nodes)
    
    if not proto:
        raise ValueError(f"Prototype node {prototype_node_id} not found")
        
    new_id = uuid.uuid4().hex
    
    instance = SceneNodeV2(
        id=new_id,
        name=f"Instance of {proto.name or proto.id}",
        mesh_id=proto.mesh_id, # Shared Mesh ID
        material_id=proto.material_id, # Shared Material ID
        transform=Transform(
            position=position,
            rotation=EulerAngles(x=0,y=0,z=0),
            scale=Vector3(x=1,y=1,z=1) 
            # Or copy scale? Usually instance has valid default transform.
        )
    )
    
    scene.nodes.append(instance)
    return new_id
