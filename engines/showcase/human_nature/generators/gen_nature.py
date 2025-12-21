"""
GENERATOR: NATURE (Grass & Ground)
----------------------------------
Generates organic environment assets.
"""
import uuid
import random
import math
from typing import List

from engines.mesh_kernel.service import MeshService
from engines.mesh_kernel.schemas import AgentMeshInstruction, MeshObject

from engines.showcase.human_nature.generators.perlin import perlin_2d

def generate_terrain(mesh_engine: MeshService, size: float = 100.0, resolution: int = 64) -> str:
    """
    Generates a Terrain Heightmap Mesh using Perlin Noise.
    Returns mesh_id.
    """
    # 1. Create Grid
    verts = []
    faces = []
    
    step = size / resolution
    offset = size / 2
    
    # Generate Vertices
    for z in range(resolution + 1):
        for x in range(resolution + 1):
            real_x = (x * step) - offset
            real_z = (z * step) - offset
            
            # Noise
            # Frequency: 0.05
            freq = 0.05
            amp = size * 0.1 # 10m height range
            
            # Layered Noise (FBM)
            y = 0
            y += perlin_2d(real_x * freq, real_z * freq) * amp
            y += perlin_2d(real_x * freq * 2, real_z * freq * 2) * (amp * 0.5)
            y += perlin_2d(real_x * freq * 4, real_z * freq * 4) * (amp * 0.25)
            
            verts.append([real_x, y, real_z])
            
    # Generate Faces (Quads)
    for z in range(resolution):
        for x in range(resolution):
            # Indices
            tl = z * (resolution + 1) + x
            tr = tl + 1
            bl = (z + 1) * (resolution + 1) + x
            br = bl + 1
            
            # Quad [tl, bl, br, tr] (CCW?)
            faces.append([tl, bl, br, tr])
            
    mesh = MeshObject(id=f"terrain_{uuid.uuid4()}", vertices=verts, faces=faces, tags=["nature:terrain"])
    mesh_engine._store[mesh.id] = mesh
    return mesh.id


def generate_grass_patch(mesh_engine: MeshService, density: int = 50, radius: float = 1.0) -> str:
    """
    Generates a merged patch of grass blades.
    Returns mesh_id.
    """
    # We construct a new MeshObject manually by merging random blades
    # A blade is a simple Triangle or 3-vert shape.
    # V0: Bottom (-w, 0, 0)
    # V1: Bottom (+w, 0, 0)
    # V2: Tip (0, h, sway)
    
    verts = []
    faces = []
    
    # We need to manually offset faces indices
    v_offset = 0
    
    for _ in range(density):
        # Random pos in circle
        angle = random.random() * math.pi * 2
        r = math.sqrt(random.random()) * radius
        x = math.cos(angle) * r
        z = math.sin(angle) * r
        
        # Blade Properties
        h = 0.5 + random.random() * 0.4 # Height 0.5 - 0.9
        w = 0.05
        
        # Rotation
        blade_rot = random.random() * math.pi * 2
        cr = math.cos(blade_rot)
        sr = math.sin(blade_rot)
        
        # Local Verts
        # V0 (Base Left)
        v0x = -w * cr
        v0z = -w * sr
        
        # V1 (Base Right)
        v1x = w * cr
        v1z = w * sr
        
        # V2 (Tip) - slightly offset for curve?
        curve_x = (random.random() - 0.5) * 0.2
        curve_z = (random.random() - 0.5) * 0.2
        v2x = curve_x
        v2z = curve_z
        
        # World Base
        b_x, b_y, b_z = x, 0, z
        
        # Append Verts
        verts.append([b_x + v0x, b_y, b_z + v0z])
        verts.append([b_x + v1x, b_y, b_z + v1z])
        verts.append([b_x + v2x, b_y + h, b_z + v2z])
        
        # Append Face (Double sided? Three.js usually needs Side=DoubleSide or duplicate face)
        # We'll just generate one face and set material to DoubleSide
        faces.append([v_offset, v_offset+1, v_offset+2])
        
        v_offset += 3
        
    patch_id = f"grass_patch_{uuid.uuid4().hex[:6]}"
    mesh = MeshObject(id=patch_id, vertices=verts, faces=faces, tags=["nature:grass"])
    mesh_engine._store[patch_id] = mesh
    return patch_id
