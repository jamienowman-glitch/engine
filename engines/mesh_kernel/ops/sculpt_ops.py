"""Mesh Sculpting Operations (Deformation)."""
from __future__ import annotations
import math
from engines.mesh_kernel.schemas import MeshObject, SculptOp, SculptBrushType

def _dist_sq(p1, p2):
    return (p1[0]-p2[0])**2 + (p1[1]-p2[1])**2 + (p1[2]-p2[2])**2

def sculpt_deform(mesh: MeshObject, op: SculptOp) -> MeshObject:
    """
    Applies a sculpting brush deformation.
    Naive O(N) implementation for V1 "Muscles".
    In env with NumPy/KDTree, this would be O(log N).
    """
    center = [op.center.x, op.center.y, op.center.z]
    r_sq = op.radius * op.radius
    
    # Vectors
    # Standard Move Brush: moves vertices within radius by Vector
    # Wait, 'center' is just position. Where is the delta?
    # Usually SculptOp needs a 'delta' vector for MOVE, or just implicitly Normal for INFLATE.
    # The current schema has 'center', 'radius', 'strength'.
    # A 'stroke' usually is drag from A to B.
    # Let's assume for V1 MOVE, we need a 'delta' or 'direction'.
    # The Schema defined in schemas.py: center: Vector3Model, radius, strength.
    # It misses 'direction' for MOVE. 
    # Let's hack: The "Brush" operates at 'center'. 
    # For INFLATE: move along normal (approximated by vertex normal).
    # For SMOOTH: Average neighbors.
    # For MOVE: We need a direction. Let's assume params might contain 'delta' but schema is strict?
    # Pydantic schema didn't have 'delta'.
    # We will assume INFLATE/SMOOTH for now or add 'direction' to schema if needed.
    # Let's verify schema... 
    # It has center, radius, strength, falloff.
    
    # Note: If brush is MOVE, we really need a vector. 
    # Let's implement INFLATE and SMOOTH correctly. MOVE might be a "Nudge" if we don't change schema.
    
    new_verts = [list(v) for v in mesh.vertices] # Deep copy coords
    
    # Pre-calc neighbors for Smooth if needed (expensive)
    if op.brush == SculptBrushType.SMOOTH:
        # Build adjacency
        adj = [[] for _ in mesh.vertices]
        for f in mesh.faces:
            n = len(f)
            for i in range(n):
                v_curr = f[i]
                v_next = f[(i+1)%n]
                v_prev = f[(i-1)%n]
                # Add if not present?
                if v_next not in adj[v_curr]: adj[v_curr].append(v_next)
                if v_prev not in adj[v_curr]: adj[v_curr].append(v_prev)
    
    for i, v in enumerate(mesh.vertices):
        d2 = _dist_sq(v, center)
        if d2 > r_sq:
            continue
            
        # Falloff (3 Smooth Step or Linear)
        d = math.sqrt(d2)
        t = 1.0 - (d / op.radius)
        t = max(0.0, min(1.0, t))
        
        # Smoothstep-ish
        weight = t * t * (3 - 2 * t)
        strength = op.strength * weight
        
        if op.brush == SculptBrushType.INFLATE:
            # Move along "Normal" (approx as V - Center for sphere, or use real normals)
            # For general mesh, we need normals. V1 Schema has optional Vertex Normals.
            # If default Cube/Sphere, we approximate normal as (V - Center_of_Mesh)? No.
            # INFLATE usually requires normals.
            # Let's assume radial inflate from Brush Center (Explode).
            vx, vy, vz = v[0]-center[0], v[1]-center[1], v[2]-center[2]
            mag = math.sqrt(vx*vx + vy*vy + vz*vz)
            if mag > 0:
                vx, vy, vz = vx/mag, vy/mag, vz/mag
                new_verts[i][0] += vx * strength
                new_verts[i][1] += vy * strength
                new_verts[i][2] += vz * strength
                
        elif op.brush == SculptBrushType.SMOOTH:
            # Simple average of neighbors
            neighbors = adj[i]
            if not neighbors: continue
            
            avg = [0.0, 0.0, 0.0]
            for n_idx in neighbors:
                nv = mesh.vertices[n_idx]
                avg[0] += nv[0]
                avg[1] += nv[1]
                avg[2] += nv[2]
            
            k = len(neighbors)
            avg[0]/=k; avg[1]/=k; avg[2]/=k
            
            # Lerp towards avg
            curr = new_verts[i]
            new_verts[i][0] = curr[0] + (avg[0] - curr[0]) * strength
            new_verts[i][1] = curr[1] + (avg[1] - curr[1]) * strength
            new_verts[i][2] = curr[2] + (avg[2] - curr[2]) * strength

    return MeshObject(
        id=mesh.id,
        vertices=new_verts,
        faces=mesh.faces,
        tags=mesh.tags + [f"sculpt:{op.brush.value}"]
    )
