"""Tests for Primitives Library (Level B)."""
from engines.scene_engine.core.geometry import BoxParams, SphereParams, Vector3
from engines.scene_engine.core.primitives import build_box_mesh, build_sphere_mesh


def test_build_box():
    params = BoxParams(width=10, height=20, depth=30)
    mesh = build_box_mesh(params)
    
    assert mesh.primitive_source == params
    assert len(mesh.vertices) == 8
    # Bounds check
    assert mesh.bounds_min.x == -5.0
    assert mesh.bounds_max.x == 5.0
    assert mesh.bounds_max.y == 10.0


def test_build_sphere():
    params = SphereParams(radius=5)
    mesh = build_sphere_mesh(params)
    
    assert mesh.primitive_source == params
    assert len(mesh.vertices) > 0
    # Bounds check roughly
    assert mesh.bounds_max.x == 5.0
