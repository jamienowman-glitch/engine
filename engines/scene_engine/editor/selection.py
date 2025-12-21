"""Editor Selection Utilities."""
from __future__ import annotations

import math
from typing import List, Optional, Tuple

from engines.scene_engine.core.scene_v2 import SceneV2, SceneNodeV2
from engines.scene_engine.core.geometry import Vector3, Mesh

# --- Selection Models ---

def raycast_scene_approx(
    scene: SceneV2, 
    ray_origin: Vector3, 
    ray_dir: Vector3
) -> List[Tuple[str, float]]:
    """
    Raycasts against nodes in scene (approximate bounding box or distance).
    Returns list of (node_id, distance), sorted by distance.
    """
    hits = []
    
    # Flatten transform world positions
    # For P0, assume nodes are flat or we computed world transforms.
    # We'll just do local-space distance check if near origin?
    # No, we need world positions.
    # Recursively traverse and track world transform.
    
    # Helper to compose transforms?
    # Keeping it simple: Just checking node positions for point-cloud style hitting 
    # or bounding sphere.
    
    def traverse(nodes, parent_tf):
        for node in nodes:
            # Compose tf
            # Simplified: World Pos = ParentPos + LocalPos
            # (ignoring rotation/scale composition complexity for P0 hit test)
            
            world_pos = Vector3(
                x=parent_tf.x + node.transform.position.x,
                y=parent_tf.y + node.transform.position.y,
                z=parent_tf.z + node.transform.position.z 
            )
            
            # Hit test (Sphere of radius 0.5)
            # Ray-Sphere intersection
            # sphere center = world_pos, r = 0.5
            
            # Vector from ray origin to sphere center
            oc = world_pos.sub(ray_origin)
            
            # Project oc onto ray_dir
            t = oc.dot(ray_dir)
            
            if t > 0:
                # Closest point on ray
                closest = ray_origin.add(ray_dir.mul(t))
                # Dist from closest to center
                d_sq = (closest.x - world_pos.x)**2 + \
                       (closest.y - world_pos.y)**2 + \
                       (closest.z - world_pos.z)**2
                       
                if d_sq < (0.5 * 0.5): # Radius 0.5
                    hits.append((node.id, t))
            
            traverse(node.children, world_pos)

    traverse(scene.nodes, Vector3(x=0,y=0,z=0))
    
    hits.sort(key=lambda x: x[1])
    return hits

def box_select(
    scene: SceneV2,
    min_pt: Vector3,
    max_pt: Vector3
) -> List[str]:
    """Selects nodes within world-space AABB."""
    selected = []
    
    def traverse(nodes, parent_pos):
        for node in nodes:
            wp = Vector3(
                x=parent_pos.x + node.transform.position.x,
                y=parent_pos.y + node.transform.position.y,
                z=parent_pos.z + node.transform.position.z
            )
            
            if (min_pt.x <= wp.x <= max_pt.x and
                min_pt.y <= wp.y <= max_pt.y and
                min_pt.z <= wp.z <= max_pt.z):
                selected.append(node.id)
                
            traverse(node.children, wp)
            
    traverse(scene.nodes, Vector3(x=0,y=0,z=0))
    return selected
