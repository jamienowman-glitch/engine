"""Mesh Primitive Operations (Math-based)."""
from __future__ import annotations

import math
from typing import List, Tuple
from engines.mesh_kernel.schemas import MeshObject

# NOTE: We use raw python math here to guarantee 0-dep execution.
# In production, this would be numba/numpy.

def create_cube(size: float = 1.0) -> MeshObject:
    """Generates a cube mesh."""
    r = size * 0.5
    # Vertices (8)
    # 0: -r, -r, -r
    # 1:  r, -r, -r
    # ...
    vertices = [
        [-r, -r, -r], [r, -r, -r], [r, r, -r], [-r, r, -r], # Back Face z=-r
        [-r, -r, r],  [r, -r, r],  [r, r, r],  [-r, r, r]   # Front Face z=r
    ]
    
    # Faces (Quads decomposed to triangles if needed, but MeshObject supports indices)
    # We'll use quads [v0, v1, v2, v3] convention for Catmull-Clark
    # But for standard renders, we usually tri, but let's stick to quads for "powerful" subd.
    faces = [
        [0, 1, 2, 3], # Back
        [4, 5, 6, 7], # Front
        [0, 4, 7, 3], # Left
        [1, 5, 6, 2], # Right
        [0, 1, 5, 4], # Bottom
        [3, 2, 6, 7]  # Top
    ]
    
    return MeshObject(
        id="", # Caller assigns ID
        vertices=vertices,
        faces=faces,
        tags=["primitive:cube"]
    )

def create_sphere(radius: float = 1.0, lat_bands: int = 16, long_bands: int = 16) -> MeshObject:
    """Generates a UV sphere."""
    vertices = []
    # indices = [] # We use faces list of lists
    faces = []
    
    # Verts
    for lat in range(lat_bands + 1):
        theta = lat * math.pi / lat_bands
        sin_theta = math.sin(theta)
        cos_theta = math.cos(theta)
        
        for lon in range(long_bands + 1):
            phi = lon * 2 * math.pi / long_bands
            sin_phi = math.sin(phi)
            cos_phi = math.cos(phi)
            
            x = cos_phi * sin_theta
            y = cos_theta
            z = sin_phi * sin_theta
            
            vertices.append([x * radius, y * radius, z * radius])
            
    # Faces
    for lat in range(lat_bands):
        for lon in range(long_bands):
            first = (lat * (long_bands + 1)) + lon
            second = first + long_bands + 1
            
            # Quad
            faces.append([first, second, second + 1, first + 1])
            
    return MeshObject(
        id="",
        vertices=vertices,
        faces=faces,
        tags=["primitive:sphere"]
    )

def create_capsule(radius: float = 0.5, length: float = 1.0, lat_bands: int = 16, long_bands: int = 16) -> MeshObject:
    """Generates a Capsule (Cylinder with Hemispherical caps)."""
    # We generate a sphere and split it at the equator.
    vertices = []
    faces = []
    
    half_len = length * 0.5
    
    # Verts
    for lat in range(lat_bands + 1):
        theta = lat * math.pi / lat_bands
        sin_theta = math.sin(theta)
        cos_theta = math.cos(theta)
        
        for lon in range(long_bands + 1):
            phi = lon * 2 * math.pi / long_bands
            sin_phi = math.sin(phi)
            cos_phi = math.cos(phi)
            
            x = cos_phi * sin_theta
            z = sin_phi * sin_theta
            y = cos_theta # -1 to 1
            
            # Deform sphere to capsule
            # Sphere radius scaling
            vx = x * radius
            vz = z * radius
            vy = y * radius
            
            # Offset for cylinder body
            # If we are in the top hemisphere (y >= 0), add half_len
            # If we are in the bottom hemisphere (y < 0), sub half_len
            # But we need to duplicate the equator vertices to have a cylinder wall?
            # Actually, standard UV sphere has vertices at discrete latitudes.
            # If we just split:
            # Lat 0..N/2 (Top) -> vy += half_len
            # Lat N/2..N (Bottom) -> vy -= half_len
            # Then the segment between N/2-1 and N/2+1 would stretch to become the cylinder body?
            # A UV sphere usually has an equator loop (if lat_bands is even).
            # Let's say lat_bands=16. Equator is at index 8.
            # If we move index 0-8 UP, and index 8-16 DOWN... index 8 is moved both up and down?
            # We need to duplicate the equator ring if we want a vertical wall without stretching the equator polys (which would be weird/diagonal).
            # Alternatively: Just generate Top Hemi, Cylinder, Bottom Hemi.
            
            # Let's use the stretching method but ensuring we insert the cylinder segment properly.
            pass

    # Clean Implementation: 3 Parts
    # Part 1: Top Hemisphere (lat 0 to lat_bands/2)
    top_verts = []
    top_start_idx = 0
    
    # Just generate points manually is safer than reusing loop complex logic
    
    # 0. Top Cap (Lat 0 to bands//2)
    # y goes from r to 0
    # Center y offset = +half_len
    
    # 1. Cylinder Body
    # Top Ring at +half_len
    # Bottom Ring at -half_len
    
    # 2. Bottom Cap
    # y goes from 0 to -r
    # Center y offset = -half_len
    
    # Let's stick to the "Stretched Sphere" logic but insert an extra ring at equator.
    # Lat bands must be even.
    if lat_bands % 2 != 0: lat_bands += 1
    equator_idx = lat_bands // 2
    
    for lat in range(lat_bands + 2): # +1 for normal bands, +1 for duplicated equator
        # Logic to map 'lat' loop index to actual sphere theta
        # 0..equator_idx -> Top Hemi
        # equator_idx -> Extruder 1
        # equator_idx+1 -> Extruder 2
        # ...
        
        # Simplified:
        # Loop 0 to equator_idx (Top Hemi + Equator Top)
        # Loop equator_idx to lat_bands (Equator Bottom + Bottom Hemi)
        
        # Proper Loop:
        # We iterate 'lat' from 0 (North Pole) to lat_bands (South Pole).
        # We calculate y. 
        # If lat < equator: y += half_len
        # If lat > equator: y -= half_len
        # If lat == equator: WE NEED TWO RINGS.
        pass
    
    # Restarting loop for final clean code
    final_verts = []
    
    for lat in range(lat_bands + 1):
        theta = lat * math.pi / lat_bands
        sin_theta = math.sin(theta)
        cos_theta = math.cos(theta)
        
        # Y on unit sphere
        y_unit = cos_theta
        
        # Decide offsets
        y_offset = 0
        if y_unit > 0.0001: 
             y_offset = half_len
        elif y_unit < -0.0001:
             y_offset = -half_len
        else:
             # Equator case (approx 0).
             # We need TWO rings here. One at +half_len, one at -half_len
             # This loop structure doesn't support "emit two rings per iteration".
             pass
             
    # OK, explicit sections logic.
    
    # Rings:
    # 0: North Pole (0, r, 0) + half_len
    # ...
    # N/2: Equator Top (..., 0, ...) + half_len
    # N/2 + 1: Equator Bottom (..., 0, ...) - half_len
    # ...
    # N+1: South Pole
    
    # Total rings = (lat_bands/2) + 1 (Top) + 1 (Bottom Equator) + (lat_bands/2) (Bottom) = lat_bands + 2 rings
    
    num_rings = lat_bands + 2
    
    for ring_i in range(num_rings):
        # Determine actual theta and y_offset
        if ring_i <= lat_bands // 2:
            # Top Hemisphere
            theta = ring_i * math.pi / lat_bands # Normal mapping 0..pi/2
            y_offset = half_len
        else:
            # Bottom Hemisphere
            # ring_i maps to (ring_i - 1) in normal numbering to skip the gap
            theta = (ring_i - 1) * math.pi / lat_bands
            y_offset = -half_len
            
        sin_theta = math.sin(theta)
        cos_theta = math.cos(theta)
        
        for lon in range(long_bands + 1):
            phi = lon * 2 * math.pi / long_bands
            sin_phi = math.sin(phi)
            cos_phi = math.cos(phi)
            
            x = cos_phi * sin_theta * radius
            z = sin_phi * sin_theta * radius
            y = (cos_theta * radius) + y_offset
            
            vertices.append([x, y, z])
            
    # Faces
    # Grid connectivity
    # We have num_rings rings, each with (long_bands + 1) verts
    
    for ring_i in range(num_rings - 1):
        for lon in range(long_bands):
            current = ring_i * (long_bands + 1) + lon
            next_row = (ring_i + 1) * (long_bands + 1) + lon
            
            # Quad [current, next_row, next_row+1, current+1] (CCW?)
            # Spheres usually: C, N, N+1, C+1 
            
            faces.append([current, current + 1, next_row + 1, next_row])
            
    return MeshObject(
        id="",
        vertices=vertices,
        faces=faces,
        tags=["primitive:capsule"]
    )
