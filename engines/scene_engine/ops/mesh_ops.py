"""Mesh Operations Module.

Provides utilities for cleaning, combining, and manipulating meshes in-memory.
"""
from __future__ import annotations

import copy
import math
import uuid
from typing import Dict, List, Tuple

from engines.scene_engine.core.geometry import Mesh, Vector3, Transform, EulerAngles

def transform_mesh(mesh: Mesh, transform: Transform) -> Mesh:
    """Bakes a transform into the mesh vertices and normals."""
    new_mesh = copy.deepcopy(mesh)
    
    # Precompute matrix-ish things
    # Translation
    tx, ty, tz = transform.position.x, transform.position.y, transform.position.z
    sx, sy, sz = transform.scale.x, transform.scale.y, transform.scale.z
    
    # Rotation (Euler XYZ)
    # Simple rotation matrix application
    # Ideally should use Matrix4 logic but kept simple/explicit here to avoid deps
    # Or use Quaternion if transform has it. Transform uses Union. 
    # For P0 let's assume Euler or convert. 
    # Actually Transform usually has rotation as EulerAngles or Quaternion.
    # We should normalize.
    
    rx, ry, rz = 0.0, 0.0, 0.0
    if isinstance(transform.rotation, EulerAngles):
        rx, ry, rz = transform.rotation.x, transform.rotation.y, transform.rotation.z
    else:
        # TODO: Quaternion support
        pass
        
    cx, sx_ = math.cos(rx), math.sin(rx)
    cy, sy_ = math.cos(ry), math.sin(ry)
    cz, sz_ = math.cos(rz), math.sin(rz)
    
    # Vertex Transform loop
    for v in new_mesh.vertices:
        # Scale
        x = v.x * sx
        y = v.y * sy
        z = v.z * sz
        
        # Rotate Z
        x_ = x * cz - y * sz_
        y_ = x * sz_ + y * cz
        x, y = x_, y_
        
        # Rotate Y
        x_ = x * cy + z * sy_
        z_ = -x * sy_ + z * cy
        x, z = x_, z_
        
        # Rotate X
        y_ = y * cx - z * sx_
        z_ = y * sx_ + z * cx
        y, z = y_, z_
        
        # Translate
        v.x = x + tx
        v.y = y + ty
        v.z = z + tz
        
    # Normal Transform loop (Rotate only, handle scale inverse transpose if non-uniform)
    # For now assuming uniform scale or ignoring normal skew
    if new_mesh.normals:
        for n in new_mesh.normals:
            x, y, z = n.x, n.y, n.z
            
            # Rotate Z
            x_ = x * cz - y * sz_
            y_ = x * sz_ + y * cz
            x, y = x_, y_
            
            # Rotate Y
            x_ = x * cy + z * sy_
            z_ = -x * sy_ + z * cy
            x, z = x_, z_
            
            # Rotate X
            y_ = y * cx - z * sx_
            z_ = y * sx_ + z * cx
            y, z = y_, z_
            
            n.x, n.y, n.z = x, y, z
            n.normalize() # In-place if implemented, or reassign
            # Since Vector3 is pydantic, modifying fields works.
            # But normalize returns new vector.
            # n = n.normalize() doesn't update list item ref?
            # Pydantic items in list are mutable objects.
            normalized = n.normalize()
            n.x = normalized.x
            n.y = normalized.y
            n.z = normalized.z
            
    return new_mesh


def scale_mesh(mesh: Mesh, factor: float) -> Mesh:
    """Uniformly scales a mesh."""
    t = Transform(
        position=Vector3(x=0,y=0,z=0),
        rotation=EulerAngles(x=0,y=0,z=0),
        scale=Vector3(x=factor, y=factor, z=factor)
    )
    return transform_mesh(mesh, t)


def recenter_mesh(mesh: Mesh) -> Mesh:
    """Moves mesh centroid to origin."""
    if not mesh.vertices:
        return mesh
        
    # Calc Centroid
    cx, cy, cz = 0.0, 0.0, 0.0
    for v in mesh.vertices:
        cx += v.x
        cy += v.y
        cz += v.z
    
    count = len(mesh.vertices)
    cx /= count
    cy /= count
    cz /= count
    
    t = Transform(
        position=Vector3(x=-cx, y=-cy, z=-cz),
        rotation=EulerAngles(x=0,y=0,z=0),
        scale=Vector3(x=1,y=1,z=1)
    )
    return transform_mesh(mesh, t)


def combine_meshes(meshes: List[Mesh]) -> Mesh:
    """Combines multiple meshes into one."""
    if not meshes:
        return Mesh(id=uuid.uuid4().hex, vertices=[], indices=[])
        
    combined = Mesh(
        id=str(uuid.uuid4()),
        name="CombinedMesh",
        vertices=[],
        normals=[],
        uvs=[],
        indices=[]
    )
    
    # If any source has normals/uvs, we attempt to keep them.
    # If a source lacks them, we pad with zero/default.
    has_normals = any(m.normals for m in meshes)
    has_uvs = any(m.uvs for m in meshes)
    
    if has_normals: combined.normals = []
    if has_uvs: combined.uvs = []
    
    vertex_offset = 0
    
    for m in meshes:
        # Verts
        combined.vertices.extend([copy.deepcopy(v) for v in m.vertices])
        
        # Normals
        if has_normals:
            if m.normals:
                combined.normals.extend([copy.deepcopy(n) for n in m.normals])
            else:
                # Pad
                combined.normals.extend([Vector3(x=0,y=1,z=0) for _ in m.vertices])
                
        # UVs
        if has_uvs:
            if m.uvs:
                combined.uvs.extend([copy.deepcopy(u) for u in m.uvs])
            else:
                from engines.scene_engine.core.geometry import UV
                combined.uvs.extend([UV(u=0,v=0) for _ in m.vertices])
        
        # Indices
        shifted_indices = [i + vertex_offset for i in m.indices]
        combined.indices.extend(shifted_indices)
        
        vertex_offset += len(m.vertices)
        
    return combined


def merge_vertices(mesh: Mesh, epsilon: float = 1e-5) -> Mesh:
    """Merges vertices that are within epsilon distance."""
    new_mesh = Mesh(
        id=mesh.id,
        name=mesh.name,
        vertices=[],
        normals=[] if mesh.normals else None,
        uvs=[] if mesh.uvs else None,
        indices=[]
    )
    
    # Map (x,y,z) quantized -> new_index
    # We use a string key or tuple for hashing
    unique_map: Dict[Tuple[int, int, int], int] = {}
    
    inv_eps = 1.0 / epsilon
    
    def quantize(v: Vector3):
        return (int(v.x * inv_eps), int(v.y * inv_eps), int(v.z * inv_eps))
    
    for i, v in enumerate(mesh.vertices):
        key = quantize(v)
        
        if key in unique_map:
            # Re-use
            new_idx = unique_map[key]
            # Accumulate normal/uv? 
            # Simple merge: first one wins.
        else:
            new_idx = len(new_mesh.vertices)
            unique_map[key] = new_idx
            new_mesh.vertices.append(copy.deepcopy(v))
            if mesh.normals:
                new_mesh.normals.append(copy.deepcopy(mesh.normals[i]))
            if mesh.uvs:
                new_mesh.uvs.append(copy.deepcopy(mesh.uvs[i]))
                
        # Remap index buffer? 
        # Wait, the iteration above is over vertices.
        # Indices refer to original vertices.
        # We need a mapping: old_index -> new_index.
    
    # We must iterate original vertices to build the map 'old_idx -> new_idx'
    old_to_new = {}
    
    # Reset and do it properly with map
    new_mesh.vertices = []
    if mesh.normals: new_mesh.normals = []
    if mesh.uvs: new_mesh.uvs = []
    unique_map = {}
    
    for i, v in enumerate(mesh.vertices):
        key = quantize(v)
        if key in unique_map:
             old_to_new[i] = unique_map[key]
        else:
            new_idx = len(new_mesh.vertices)
            unique_map[key] = new_idx
            old_to_new[i] = new_idx
            
            new_mesh.vertices.append(copy.deepcopy(v))
            if mesh.normals:
                new_mesh.normals.append(copy.deepcopy(mesh.normals[i]))
            if mesh.uvs:
                new_mesh.uvs.append(copy.deepcopy(mesh.uvs[i]))
                
    # Rebuild indices
    for idx in mesh.indices:
        new_mesh.indices.append(old_to_new[idx])
        
    return new_mesh


def recompute_normals(mesh: Mesh) -> Mesh:
    """Recomputes flat face normals. (Smooth requires smoothing groups logic)."""
    if len(mesh.indices) % 3 != 0:
        return mesh # Invalid topo
        
    new_mesh = copy.deepcopy(mesh)
    
    # Init zero normals
    new_mesh.normals = [Vector3(x=0,y=0,z=0) for _ in new_mesh.vertices]
    
    # Accumulate face normals
    for i in range(0, len(mesh.indices), 3):
        i0, i1, i2 = mesh.indices[i], mesh.indices[i+1], mesh.indices[i+2]
        v0 = new_mesh.vertices[i0]
        v1 = new_mesh.vertices[i1]
        v2 = new_mesh.vertices[i2]
        
        # Edge vectors
        e1 = v1.sub(v0)
        e2 = v2.sub(v0)
        
        normal = e1.cross(e2).normalize()
        
        # Add to all 3 verts (weighted by area? No, simple average)
        new_mesh.normals[i0] = new_mesh.normals[i0].add(normal)
        new_mesh.normals[i1] = new_mesh.normals[i1].add(normal)
        new_mesh.normals[i2] = new_mesh.normals[i2].add(normal)
        
    # Normalize result
    for n in new_mesh.normals:
        normalized = n.normalize()
        n.x, n.y, n.z = normalized.x, normalized.y, normalized.z
        
    return new_mesh
