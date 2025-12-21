"""Level of Detail (LoD) System."""
from __future__ import annotations

import math
from typing import List, Optional, Dict
from pydantic import BaseModel

from engines.scene_engine.core.scene_v2 import SceneV2, SceneNodeV2
from engines.scene_engine.core.geometry import Vector3

class LODLevel(BaseModel):
    max_distance: float
    mesh_id: str

class LODGroup(BaseModel):
    levels: List[LODLevel] 
    # Levels should be sorted by distance?
    # Logic: if dist < max_distance, use this mesh.
    # Usually we iterate sorted by distance ascending.

def apply_lod(scene: SceneV2, camera_pos: Vector3, active_lods: Dict[str, LODGroup]):
    """
    Updates scene nodes based on camera distance and provided LOD definitions.
    active_lods: Map of Node ID -> LODGroup definition.
    (In a real engine, LODGroup might be a component on the Node itself).
    """
    
    # Helper recursive traversal
    def traverse(nodes, parent_pos):
        for node in nodes:
            world_pos = Vector3(
                x=parent_pos.x + node.transform.position.x,
                y=parent_pos.y + node.transform.position.y,
                z=parent_pos.z + node.transform.position.z 
            )
            
            if node.id in active_lods:
                # Calculate distance
                dx = world_pos.x - camera_pos.x
                dy = world_pos.y - camera_pos.y
                dz = world_pos.z - camera_pos.z
                dist = math.sqrt(dx*dx + dy*dy + dz*dz)
                
                # Select Level
                group = active_lods[node.id]
                selected_mesh = None
                
                # Assuming levels sorted by max_distance?
                # Or find the first level where dist < max_distance
                # If dist > all, use last? or Cull?
                
                # Sort levels just in case
                sorted_levels = sorted(group.levels, key=lambda l: l.max_distance)
                
                for level in sorted_levels:
                    if dist < level.max_distance:
                        selected_mesh = level.mesh_id
                        break
                        
                # If exceeded all, use last (lowest detail)
                if not selected_mesh and sorted_levels:
                    selected_mesh = sorted_levels[-1].mesh_id
                    
                if selected_mesh:
                    node.mesh_id = selected_mesh
            
            traverse(node.children, world_pos)
            
    traverse(scene.nodes, Vector3(x=0,y=0,z=0))
    return scene
