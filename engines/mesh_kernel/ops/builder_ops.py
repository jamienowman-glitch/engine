"""
MESH BUILDER OPS
----------------
Helper class for Box Modeling (Extrude, Transform, etc).
"""
import copy
from typing import List, Tuple, Optional
from engines.mesh_kernel.schemas import MeshObject

# Helper math
def _add(v, d): return [v[0]+d[0], v[1]+d[1], v[2]+d[2]]
def _sub(v, d): return [v[0]-d[0], v[1]-d[1], v[2]-d[2]]
def _mul(v, s): return [v[0]*s, v[1]*s, v[2]*s]
def _center(verts):
    c = [0,0,0]
    for v in verts: c = _add(c, v)
    return _mul(c, 1.0/len(verts))

class MeshBuilder:
    def __init__(self, base_mesh: MeshObject):
        # We operate on a deep copy or existing? Let's modify in place if passed.
        # But usually we want to return new.
        # Let's verify if we need to clone. For Generator, in-place is fine.
        self.mesh = base_mesh
        
    def get_face_center(self, face_idx: int) -> List[float]:
        face = self.mesh.faces[face_idx]
        pts = [self.mesh.vertices[i] for i in face]
        return _center(pts)

    def select_face_by_normal(self, direction: List[float], tolerance: float = 0.5) -> int:
        """Finds face pointing in direction."""
        # Simple dot product check
        best = -1.0
        best_idx = -1
        
        dir_len = (direction[0]**2 + direction[1]**2 + direction[2]**2)**0.5
        norm_dir = _mul(direction, 1.0/dir_len)
        
        for idx, face in enumerate(self.mesh.faces):
            # Calc normal
            if len(face) < 3: continue
            p0 = self.mesh.vertices[face[0]]
            p1 = self.mesh.vertices[face[1]]
            p2 = self.mesh.vertices[face[2]]
            
            # Cross product (p1-p0) x (p2-p0)
            u = _sub(p1, p0)
            v = _sub(p2, p0)
            nx = u[1]*v[2] - u[2]*v[1]
            ny = u[2]*v[0] - u[0]*v[2]
            nz = u[0]*v[1] - u[1]*v[0]
            
            nl = (nx**2 + ny**2 + nz**2)**0.5
            if nl == 0: continue
            normal = [nx/nl, ny/nl, nz/nl]
            
            dot = normal[0]*norm_dir[0] + normal[1]*norm_dir[1] + normal[2]*norm_dir[2]
            if dot > best:
                best = dot
                best_idx = idx
                
        return best_idx

    def extrude_face(self, face_idx: int, amount: float) -> int:
        """
        Extrudes a face along its normal (or simple translation).
        Returns the index of the NEW tip face.
        """
        if face_idx < 0 or face_idx >= len(self.mesh.faces): return -1
        
        face = self.mesh.faces[face_idx]
        original_verts_indices = list(face) # Copy
        
        # 1. Create New Vertices (Tip)
        # They start at same position as base verts
        new_indices = []
        for vi in original_verts_indices:
            v_pos = self.mesh.vertices[vi]
            # Add new vertex
            self.mesh.vertices.append(list(v_pos)) # Copy pos
            new_indices.append(len(self.mesh.vertices)-1)
            
        # 2. Calculate Face Normal for extrusion direction
        # Simple avg normal or just use provided amount as magnitude along implicit normal?
        # We'll calculate normal manually
        p0 = self.mesh.vertices[original_verts_indices[0]]
        p1 = self.mesh.vertices[original_verts_indices[1]]
        p2 = self.mesh.vertices[original_verts_indices[2]]
        u = _sub(p1, p0)
        v = _sub(p2, p0)
        nx = u[1]*v[2] - u[2]*v[1]
        ny = u[2]*v[0] - u[0]*v[2]
        nz = u[0]*v[1] - u[1]*v[0]
        nl = (nx**2 + ny**2 + nz**2)**0.5
        normal = [0,1,0]
        if nl > 0: normal = [nx/nl, ny/nl, nz/nl]
        
        offset = _mul(normal, amount)
        
        # Move new vertices
        for ni in new_indices:
            self.mesh.vertices[ni] = _add(self.mesh.vertices[ni], offset)
            
        # 3. Create Side Faces (Quads) connects Old -> New
        # Assuming CCW winding
        n = len(face)
        for i in range(n):
            v_curr = original_verts_indices[i]
            v_next = original_verts_indices[(i+1)%n]
            
            nv_curr = new_indices[i]
            nv_next = new_indices[(i+1)%n]
            
            # Side Face: v_curr, v_next, nv_next, nv_curr (CCW?)
            # v_curr is bottom right?
            # Let's visualize: 
            # Top: nv's. Bottom: v's.
            # Side must wind CCW looking from outside.
            # v_next is "left" of v_curr on the ring?
            self.mesh.faces.append([v_curr, v_next, nv_next, nv_curr])
            
        # 4. Update Original Face to use New Vertices (This becomes the "Tip")
        # Or remove old face and add new one?
        # Updating is cleaner to keep ID stable if user tracks it
        self.mesh.faces[face_idx] = new_indices
        
        # Return index of the tip face (which is still face_idx)
        return face_idx

    def translate_face(self, face_idx: int, vec: List[float]):
        """Moves a face."""
        if face_idx < 0: return
        for vi in self.mesh.faces[face_idx]:
             self.mesh.vertices[vi] = _add(self.mesh.vertices[vi], vec)

    def scale_face(self, face_idx: int, scale: float):
        """Scales a face relative to its center."""
        if face_idx < 0: return
        center = self.get_face_center(face_idx)
        for vi in self.mesh.faces[face_idx]:
            p = self.mesh.vertices[vi]
            # v' = c + (p-c)*s
            rel = _sub(p, center)
            rel = _mul(rel, scale)
            self.mesh.vertices[vi] = _add(center, rel)

