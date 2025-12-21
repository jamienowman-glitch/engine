
import pytest
import math
from engines.scene_engine.core.geometry import Vector3
from engines.scene_engine.curves.models import (
    Curve, CurveKind, SplineNode,
    PolylineData, BezierData, NurbsCurveData,
    Surface, SurfaceKind, NurbsSurfaceData
)
from engines.scene_engine.curves.service import evaluate_curve, evaluate_surface, tessellate_curve

def test_bezier_linear():
    # Degree 1 bezier (Line)
    c = Curve(
        id="b1",
        kind=CurveKind.BEZIER,
        bezier=BezierData(points=[
            Vector3(x=0,y=0,z=0),
            Vector3(x=10,y=0,z=0)
        ])
    )
    
    mid = evaluate_curve(c, 0.5)
    assert abs(mid.x - 5.0) < 1e-5
    assert abs(mid.y) < 1e-5

def test_bezier_quadratic():
    # Standard quadratic 0,0 -> 5,10 -> 10,0
    # Peak at t=0.5 should be (5, 5) 
    # Logic: Lerp(Lerp(p0,p1), Lerp(p1,p2))
    # mid 0-1 = (2.5, 5)
    # mid 1-2 = (7.5, 5)
    # mid mid = (5, 5)
    c = Curve(
        id="b2",
        kind=CurveKind.BEZIER,
        bezier=BezierData(points=[
            Vector3(x=0,y=0,z=0),
            Vector3(x=5,y=10,z=0),
            Vector3(x=10,y=0,z=0)
        ])
    )
    
    mid = evaluate_curve(c, 0.5)
    assert abs(mid.x - 5.0) < 1e-5
    assert abs(mid.y - 5.0) < 1e-5

def test_nurbs_circle_arc():
    # 90 deg arc (quarter circle)
    # Degree 2. 
    # Control points: (1,0), (1,1), (0,1)
    # Weights: 1, w=sin(45)?? Actually w=sqrt(2)/2 approx 0.7071 creates circle.
    # Knots: [0,0,0, 1,1,1] (clamped)
    
    w = math.sqrt(2.0) / 2.0
    
    c = Curve(
        id="n_arc",
        kind=CurveKind.NURBS,
        nurbs=NurbsCurveData(
            degree=2,
            knots=[0.0, 0.0, 0.0, 1.0, 1.0, 1.0],
            control_points=[
                SplineNode(position=Vector3(x=1,y=0,z=0), weight=1.0),
                SplineNode(position=Vector3(x=1,y=1,z=0), weight=w),
                SplineNode(position=Vector3(x=0,y=1,z=0), weight=1.0)
            ]
        )
    )
    
    # At t=0.5, exact circle point is (cos45, sin45) = (0.707, 0.707)
    pt = evaluate_curve(c, 0.5)
    
    expected = 0.70710678
    assert abs(pt.x - expected) < 1e-4
    assert abs(pt.y - expected) < 1e-4

def test_nurbs_surface_plane():
    # Flat plane via NURBS. Degree 1x1 (Linear)
    # 4 control points: (0,0), (1,0), (0,1), (1,1) (Z=0)
    # Knots U: [0,0, 1,1]
    # Knots V: [0,0, 1,1]
    
    grid = [
        [SplineNode(position=Vector3(x=0,y=0,z=0)), SplineNode(position=Vector3(x=0,y=1,z=0))], # U=0 col
        [SplineNode(position=Vector3(x=1,y=0,z=0)), SplineNode(position=Vector3(x=1,y=1,z=0))]  # U=1 col
    ]
    
    s = Surface(
        id="s1",
        kind=SurfaceKind.NURBS,
        nurbs=NurbsSurfaceData(
            degree_u=1,
            degree_v=1,
            knots_u=[0.0, 0.0, 1.0, 1.0],
            knots_v=[0.0, 0.0, 1.0, 1.0],
            control_points=grid
        )
    )
    
    mid = evaluate_surface(s, 0.5, 0.5)
    
    # Should be (0.5, 0.5, 0)
    assert abs(mid.x - 0.5) < 1e-5
    assert abs(mid.y - 0.5) < 1e-5

def test_tessellate():
    c = Curve(
        id="line", 
        kind=CurveKind.POLYLINE,
        polyline=PolylineData(points=[Vector3(x=0,y=0,z=0), Vector3(x=10,y=0,z=0)])
    )
    
    mesh = tessellate_curve(c, segments=10)
    assert len(mesh.vertices) == 11
    assert len(mesh.indices) == 20 # 10 lines * 2 indices
