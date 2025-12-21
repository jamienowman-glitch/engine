"""Editor Snapping Utilities."""
from __future__ import annotations

import math
from typing import List, Optional

from engines.scene_engine.core.geometry import Vector3, Mesh
from engines.scene_engine.core.scene_v2 import SceneV2

def snap_to_grid(pos: Vector3, step: float = 1.0) -> Vector3:
    """Snaps a position to the nearest grid increment."""
    if step <= 0: return pos
    
    def _snap(val):
        return round(val / step) * step
        
    return Vector3(
        x=_snap(pos.x),
        y=_snap(pos.y),
        z=_snap(pos.z)
    )

def snap_to_vertex(
    pos: Vector3, 
    scene: SceneV2, 
    threshold: float = 0.5
) -> Optional[Vector3]:
    """
    Finds nearest vertex in scene meshes within threshold.
    Note: Very expensive O(N) over all verts for P0.
    """
    best_pt = None
    min_dist_sq = threshold * threshold
    
    # We need world positions. 
    # P0 Simplification: Only check root-level nodes? 
    # Or traverse fully? Traverse fully.
    
    def traverse(nodes, parent_tf):
        nonlocal best_pt, min_dist_sq
        
        for node in nodes:
            world_pos = Vector3(
                 x=parent_tf.x + node.transform.position.x,
                 y=parent_tf.y + node.transform.position.y,
                 z=parent_tf.z + node.transform.position.z
            )
            
            if node.mesh_id:
                # Find mesh
                mesh = next((m for m in scene.meshes if m.id == node.mesh_id), None)
                if mesh:
                    for v in mesh.vertices:
                        # Vertex local pos + scale/rot? 
                        # Assuming node scale/rot identity for P0 vertex snap, 
                        # just translation.
                        vx = world_pos.x + v.x
                        vy = world_pos.y + v.y
                        vz = world_pos.z + v.z
                        
                        dist_sq = (vx - pos.x)**2 + (vy - pos.y)**2 + (vz - pos.z)**2
                        if dist_sq < min_dist_sq:
                            min_dist_sq = dist_sq
                            best_pt = Vector3(x=vx, y=vy, z=vz)
            
            traverse(node.children, world_pos)

    traverse(scene.nodes, Vector3(x=0,y=0,z=0))
    
    return best_pt
