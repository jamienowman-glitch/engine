"""Mesh Subdivision Operations (Catmull-Clark)."""
from __future__ import annotations
from typing import List, Dict, Tuple
from engines.mesh_kernel.schemas import MeshObject

# Helper: Simple Vector Add/Scale
def _add(a, b): return [a[0]+b[0], a[1]+b[1], a[2]+b[2]]
def _scale(v, s): return [v[0]*s, v[1]*s, v[2]*s]
def _div(v, s): return [v[0]/s, v[1]/s, v[2]/s]

def subdivide_cc(mesh: MeshObject, iterations: int = 1) -> MeshObject:
    """
    Performs Catmull-Clark Subdivision.
    Works on Quad meshes best. Triangles will be converted to Quads (3 quads per tri).
    """
    current_mesh = mesh
    for _ in range(iterations):
        current_mesh = _cc_iteration(current_mesh)
    return current_mesh

def _cc_iteration(mesh: MeshObject) -> MeshObject:
    # Create lookup for creases
    # Set of tuples (u, v) sorted
    creases = set()
    if getattr(mesh, "crease_edges", None):
        for e in mesh.crease_edges:
            creases.add(tuple(sorted((int(e[0]), int(e[1])))))

    # ... (Face Points calc: Unchanged) ...
    # 1. Face Points: Average of face vertices
    face_points = []
    for face in mesh.faces:
        center = [0.0, 0.0, 0.0]
        for idx in face:
            center = _add(center, mesh.vertices[idx])
        face_points.append(_div(center, float(len(face))))

    # 2. Edge Data Structure
    # Map edge_key (min, max) -> [vals]
    # We need to find "Edge Points": average of (end points + face points of adjacent faces)
    edge_map: Dict[Tuple[int, int], List[int]] = {} # (v1, v2) -> [face_idx, ...]
    
    # Build edge-face connectivity
    for f_idx, face in enumerate(mesh.faces):
        n = len(face)
        for i in range(n):
            v1 = face[i]
            v2 = face[(i+1)%n]
            edge = tuple(sorted((v1, v2)))
            if edge not in edge_map:
                edge_map[edge] = []
            edge_map[edge].append(f_idx)

    # Calculate Edge Points
    edge_points = {} # (v1, v2) -> Point [x,y,z]
    edge_idx_map = {} # (v1, v2) -> new_vertex_index
    
    next_idx = 0
    
    # We'll build the new vertex list order:
    # [Face Points] ... [Edge Points] ... [Original Vertex Points]
    # But to keep it simple, we just append continuously.
    new_vertices = []
    
    # Add Face Points first
    # face_point_indices = [0 ... len(faces)-1]
    new_vertices.extend(face_points)
    next_idx += len(face_points)
    
    # Add Edge Points
    for edge, faces_adj in edge_map.items():
        midpoint = _div(_add(mesh.vertices[edge[0]], mesh.vertices[edge[1]]), 2.0)
        
        is_crease = (edge in creases)
        
        if is_crease:
            # Sharp Edge Rule: E = Midpoint
            e_pt = midpoint
        elif len(faces_adj) == 2:
             # Smooth Rule
            fp1 = face_points[faces_adj[0]]
            fp2 = face_points[faces_adj[1]]
            avg_fp = _div(_add(fp1, fp2), 2.0)
            e_pt = _div(_add(midpoint, avg_fp), 2.0)
        else:
            e_pt = midpoint # Boundary edge
            
        edge_points[edge] = e_pt
        edge_idx_map[edge] = next_idx
        new_vertices.append(e_pt)
        next_idx += 1
        
    # 3. New Vertex Points (move original vertices)
    # Rules:
    # - 0 Sharp Edges: Smooth Rule
    # - 2 Sharp Edges: Crease Rule (Moving on crease curve)
    # - >2 Sharp Edges: Corner Rule (Fixed)
    # - 1 Sharp Edge: Treated as Boundary/Corner (Fixed? Or blend? Usually Corner/Dart)
    
    # We need adjacency: Vertex -> faces, Vertex -> edges
    vert_faces = [[] for _ in mesh.vertices]
    vert_edges = [[] for _ in mesh.vertices]
    
    for f_idx, face in enumerate(mesh.faces):
        for v_idx in face:
            vert_faces[v_idx].append(f_idx)
            
    for edge in edge_map.keys():
        v1, v2 = edge
        vert_edges[v1].append(edge)
        vert_edges[v2].append(edge)
        
    old_to_new_map = {}
    
    for v_idx, P in enumerate(mesh.vertices):
        # Determine Sharpness Incident
        sharp_incident = []
        for e in vert_edges[v_idx]:
             if e in creases:
                 sharp_incident.append(e)
                 
        n_sharp = len(sharp_incident)
        n = len(vert_edges[v_idx])
        
        if n_sharp >= 3:
            # Corner -> Fixed
            new_pos = P
        elif n_sharp == 2:
            # Crease Rule
            # NewV = (0.75 * P) + (0.125 * Neighbor1) + (0.125 * Neighbor2)
            # Find neighbors on sharp edges
            neighbors = []
            for e in sharp_incident:
                other = e[1] if e[0] == v_idx else e[0]
                neighbors.append(mesh.vertices[other])
            
            term1 = _scale(P, 6.0) # 0.75 * 8 = 6
            term2 = _add(neighbors[0], neighbors[1]) # 0.125 + 0.125 = 0.25 * 8 = 2? No
            # Formula: (6P + N1 + N2) / 8 ??
            # 6/8 = 0.75. 1/8 = 0.125. yes.
            
            s = _add(term1, term2)
            new_pos = _div(s, 8.0)
            
        elif n_sharp == 1:
            # Dart/Boundary -> Corner (Fixed)
            new_pos = P
        elif n < 3: 
            # Boundary vertex/Corner in mesh topology terms
            new_pos = P 
        else:
            # Smooth Rule
            # F = Avg Face Points
            F = [0.0, 0.0, 0.0]
            for f_i in vert_faces[v_idx]:
                F = _add(F, face_points[f_i])
            F = _div(F, float(len(vert_faces[v_idx]))) 
            
            # R = Avg Edge Midpoints (ALL edges, not just sharp)
            R = [0.0, 0.0, 0.0]
            for edge in vert_edges[v_idx]:
                mid = _div(_add(mesh.vertices[edge[0]], mesh.vertices[edge[1]]), 2.0)
                R = _add(R, mid)
            R = _div(R, float(n))
            
            # (F + 2R + (n-3)P) / n
            term1 = F
            term2 = _scale(R, 2.0)
            term3 = _scale(P, float(n-3))
            sum_all = _add(_add(term1, term2), term3)
            new_pos = _div(sum_all, float(n))
            
        old_to_new_map[v_idx] = next_idx
        new_vertices.append(new_pos)
        next_idx += 1
        
    # 4. Construct New Faces (Quads)
    # Unchanged logic
    new_faces = []
    
    for f_idx, face in enumerate(mesh.faces):
        num_v = len(face)
        fp_idx = f_idx # Face point index (it was first in list)
        
        for i in range(num_v):
            v_curr = face[i]
            v_next = face[(i+1)%num_v]
            v_prev = face[(i-1)%num_v]
            
            edge_next = tuple(sorted((v_curr, v_next)))
            edge_prev = tuple(sorted((v_curr, v_prev)))
            
            ep_next_idx = edge_idx_map[edge_next]
            ep_prev_idx = edge_idx_map[edge_prev]
            new_v_idx = old_to_new_map[v_curr]
            
            new_faces.append([new_v_idx, ep_next_idx, fp_idx, ep_prev_idx])
    
    # Propagate Creases?
    # New edges: 
    # 1. (NewV, EP) - Part of original edge. Should inherit sharpness?
    # Yes. If original edge (V, Next) was sharp, then (NewV, EP_next) is sharp.
    # 2. (EP, FP) - Interior edge. Smooth usually.
    
    new_creases = []
    for edge in creases:
        # Original edge (v1, v2)
        # Becomes 2 edges: (NewV1, EP) and (EP, NewV2)
        v1, v2 = edge
        if edge in edge_idx_map:
            ep_idx = edge_idx_map[edge]
            nv1 = old_to_new_map[v1]
            nv2 = old_to_new_map[v2]
            
            new_creases.append([nv1, ep_idx])
            new_creases.append([ep_idx, nv2])
            
    return MeshObject(
        id=mesh.id,
        vertices=new_vertices,
        faces=new_faces,
        tags=mesh.tags + ["processed:subd"],
        crease_edges=new_creases
    )
