
import pytest
from engines.scene_engine.core.geometry import Mesh, Vector3, Transform, EulerAngles
from engines.scene_engine.ops.mesh_ops import (
    combine_meshes, merge_vertices, recompute_normals, 
    recenter_mesh, scale_mesh, transform_mesh
)

def _create_tri(offset=0):
    """Creates a simple triangle mesh."""
    return Mesh(
        id=f"m_{offset}",
        vertices=[
            Vector3(x=0+offset, y=0, z=0),
            Vector3(x=1+offset, y=0, z=0),
            Vector3(x=0+offset, y=1, z=0)
        ],
        indices=[0, 1, 2],
        normals=[Vector3(x=0, y=0, z=1) for _ in range(3)] 
    )

def test_combine_meshes():
    m1 = _create_tri(0)
    m2 = _create_tri(10)
    
    combined = combine_meshes([m1, m2])
    
    assert len(combined.vertices) == 6
    assert len(combined.indices) == 6
    # Check indices shift
    assert combined.indices[3] == 3 # 0+3
    assert combined.indices[5] == 5 # 2+3

def test_merge_vertices():
    # Create mesh with duplicate verts
    m = Mesh(
        id="dup",
        vertices=[
            Vector3(x=0, y=0, z=0),
            Vector3(x=0, y=0, z=0), # Duplicate
            Vector3(x=1, y=0, z=0)
        ],
        indices=[0, 1, 2] # Degenerate tri but valid technically
    )
    
    merged = merge_vertices(m, epsilon=0.1)
    
    assert len(merged.vertices) == 2
    # Indices should be remapped. 
    # original 0 -> 0
    # original 1 -> 0
    # original 2 -> 1
    assert merged.indices == [0, 0, 1]

def test_recenter_mesh():
    m = _create_tri() # Centroid of (0,0), (1,0), (0,1) is (0.33, 0.33, 0)
    
    centered = recenter_mesh(m)
    
    # Sum should be near 0
    sx = sum(v.x for v in centered.vertices)
    sy = sum(v.y for v in centered.vertices)
    
    assert abs(sx) < 1e-5
    assert abs(sy) < 1e-5

def test_scale_mesh():
    m = _create_tri()
    scaled = scale_mesh(m, 2.0)
    
    # Original vert 1 was (1,0,0). New should be (2,0,0)
    assert abs(scaled.vertices[1].x - 2.0) < 1e-5

def test_transform_mesh():
    m = _create_tri()
    t = Transform(
        position=Vector3(x=10, y=0, z=0),
        rotation=EulerAngles(x=0,y=0,z=0),
        scale=Vector3(x=1,y=1,z=1)
    )
    
    moved = transform_mesh(m, t)
    # v0 (0,0,0) -> (10,0,0)
    assert abs(moved.vertices[0].x - 10.0) < 1e-5

def test_recompute_normals():
    # Triangle in XY plane (Z=0). Normal should be +Z (0,0,1)
    m = Mesh(
        id="raw",
        vertices=[
            Vector3(x=0, y=0, z=0),
            Vector3(x=1, y=0, z=0),
            Vector3(x=0, y=1, z=0)
        ],
        indices=[0, 1, 2]
    )
    # No normals initial
    
    computed = recompute_normals(m)
    
    assert len(computed.normals) == 3
    n0 = computed.normals[0]
    
    assert abs(n0.x) < 1e-5
    assert abs(n0.y) < 1e-5
    assert abs(n0.z - 1.0) < 1e-5
    
    # Check orientation (RH rule)
    # 0->1 is +X. 0->2 is +Y. Cross(X, Y) = Z. Correct.
