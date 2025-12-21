"""Curves and Surfaces Service."""
from __future__ import annotations

import math
from typing import List, Tuple

from engines.scene_engine.core.geometry import Vector3, Mesh
from engines.scene_engine.curves.models import (
    Curve, CurveKind, 
    SplineNode, 
    PolylineData, BezierData, NurbsCurveData,
    Surface, SurfaceKind, NurbsSurfaceData
)

def _lerp(a: Vector3, b: Vector3, t: float) -> Vector3:
    return Vector3(
        x=a.x + (b.x - a.x) * t,
        y=a.y + (b.y - a.y) * t,
        z=a.z + (b.z - a.z) * t
    )

# --- Polyline ---

def _eval_polyline(data: PolylineData, t: float) -> Vector3:
    points = data.points
    if not points:
        return Vector3(x=0,y=0,z=0)
    if len(points) == 1:
        return points[0]
        
    # t is 0..1 along total length? 
    # For simple P0, let's treat t as parametric across segments uniformly? 
    # Or strict length.
    # Uniform parameterization is easier.
    
    count = len(points)
    # Segments = count - 1 (if open)
    segs = count - 1
    if segs == 0: return points[0]
    
    scaled_t = t * segs
    idx = int(scaled_t)
    if idx >= segs:
        # Clamped to end
        return points[-1]
    
    sub_t = scaled_t - idx
    
    p0 = points[idx]
    p1 = points[idx+1]
    
    return _lerp(p0, p1, sub_t)

# --- Bezier ---

def _eval_bezier(data: BezierData, t: float) -> Vector3:
    # De Casteljau's algorithm for arbitrary degree
    points = [p for p in data.points] # copy
    n = len(points)
    if n == 0: return Vector3(x=0,y=0,z=0)
    
    for r in range(1, n):
        for i in range(n - r):
            points[i] = _lerp(points[i], points[i+1], t)
            
    return points[0]

# --- NURBS (Curve) ---

def _find_span(n: int, p: int, u: float, knots: List[float]) -> int:
    """Finds knot span index."""
    # n = number of control points - 1
    # p = degree
    # u = parameter
    
    # Handle end case
    if u >= knots[n + 1]:
        return n
        
    # Binary search
    low = p
    high = n + 1
    mid = int((low + high) / 2)
    
    while u < knots[mid] or u >= knots[mid + 1]:
        if u < knots[mid]:
            high = mid
        else:
            low = mid
        mid = int((low + high) / 2)
        
    return mid

def _basis_funs(span: int, u: float, p: int, knots: List[float]) -> List[float]:
    """Computes non-vanishing basis functions."""
    N = [0.0] * (p + 1)
    left = [0.0] * (p + 1)
    right = [0.0] * (p + 1)
    N[0] = 1.0
    
    for j in range(1, p + 1):
        left[j] = u - knots[span + 1 - j]
        right[j] = knots[span + j] - u
        saved = 0.0
        
        for r in range(j):
            temp = N[r] / (right[r + 1] + left[j - r])
            N[r] = saved + right[r + 1] * temp
            saved = left[j - r] * temp
            
        N[j] = saved
        
    return N

def _eval_nurbs_curve(data: NurbsCurveData, t: float) -> Vector3:
    # degree p
    p = data.degree
    knots = data.knots
    cps = data.control_points
    
    # Clamp t to knot domain [knots[p], knots[len-p-1]]?
    # Usually valid domain is [knots[p], knots[m-p]] where m = len(knots)-1.
    start_u = knots[p]
    end_u = knots[len(knots) - 1 - p]
    
    # Remap t(0..1) to (start_u..end_u)
    u = start_u + t * (end_u - start_u)
    
    # n = num_cps - 1
    n = len(cps) - 1
    
    span = _find_span(n, p, u, knots)
    N = _basis_funs(span, u, p, knots)
    
    C = Vector3(x=0,y=0,z=0)
    w_sum = 0.0
    
    # Rational NURBS: Compute weighted sum, then divide by sum of weights
    for i in range(p + 1):
        idx = span - p + i
        cp = cps[idx]
        weight = cp.weight
        basis = N[i]
        
        val = basis * weight
        w_sum += val
        
        C.x += cp.position.x * val
        C.y += cp.position.y * val
        C.z += cp.position.z * val
        
    if w_sum != 0 and w_sum != 1.0:
        C.x /= w_sum
        C.y /= w_sum
        C.z /= w_sum
        
    return C

# --- Evaluation Entry ---

def evaluate_curve(curve: Curve, t: float) -> Vector3:
    """Evaluates curve at t (0.0 to 1.0)."""
    t = max(0.0, min(1.0, t)) # Clamp
    
    if curve.kind == CurveKind.POLYLINE and curve.polyline:
        return _eval_polyline(curve.polyline, t)
    
    elif curve.kind == CurveKind.BEZIER and curve.bezier:
        return _eval_bezier(curve.bezier, t)
        
    elif curve.kind == CurveKind.NURBS and curve.nurbs:
        return _eval_nurbs_curve(curve.nurbs, t)
        
    # Fallback
    return Vector3(x=0,y=0,z=0)

# --- Surface ---

def _eval_nurbs_surface(data: NurbsSurfaceData, u: float, v: float) -> Vector3:
    p = data.degree_u
    q = data.degree_v
    knots_u = data.knots_u
    knots_v = data.knots_v
    grid = data.control_points # [u][v]
    
    # Domain U
    u_start = knots_u[p]
    u_end = knots_u[len(knots_u) - 1 - p]
    U = u_start + u * (u_end - u_start)
    
    # Domain V
    v_start = knots_v[q]
    v_end = knots_v[len(knots_v) - 1 - q]
    V = v_start + v * (v_end - v_start)
    
    # n = num_u - 1
    n = len(grid) - 1
    # m = num_v - 1
    m = len(grid[0]) - 1
    
    span_u = _find_span(n, p, U, knots_u)
    Nu = _basis_funs(span_u, U, p, knots_u)
    
    span_v = _find_span(m, q, V, knots_v)
    Nv = _basis_funs(span_v, V, q, knots_v)
    
    S = Vector3(x=0,y=0,z=0)
    w_sum = 0.0
    
    # Double loop for surface point
    for k in range(q + 1): # V loop
        temp_v = Vector3(x=0,y=0,z=0) # Weighted sum for this U row
        temp_w = 0.0
        
        idx_v = span_v - q + k
        weight_v = Nv[k]
        
        for l in range(p + 1): # U loop
            idx_u = span_u - p + l
            
            cp = grid[idx_u][idx_v]
            weight = cp.weight
            basis = Nu[l]
            
            # Basis product Nu * Nv
            # Here we can compose:
            # S(u, v) = sum(Nu[l] * Nv[k] * P[idx_u][idx_v] * w) / sum(...)
            
            val = basis * weight_v * weight # Nu * Nv * W
            
            S.x += cp.position.x * val
            S.y += cp.position.y * val
            S.z += cp.position.z * val
            w_sum += val
            
    if w_sum != 0:
        S.x /= w_sum
        S.y /= w_sum
        S.z /= w_sum
        
    return S

def evaluate_surface(surface: Surface, u: float, v: float) -> Vector3:
    u = max(0.0, min(1.0, u))
    v = max(0.0, min(1.0, v))
    
    if surface.kind == SurfaceKind.NURBS and surface.nurbs:
        return _eval_nurbs_surface(surface.nurbs, u, v)
        
    return Vector3(x=0,y=0,z=0)

# --- Tessellation ---

def tessellate_curve(curve: Curve, segments: int = 20) -> Mesh:
    """Converts curve to a line-strip Mesh."""
    import uuid
    verts = []
    
    for i in range(segments + 1):
        t = i / float(segments)
        verts.append(evaluate_curve(curve, t))
        
    # Indices: 0-1, 1-2, 2-3...
    indices = []
    for i in range(segments):
        indices.extend([i, i+1])
        
    return Mesh(
        id=uuid.uuid4().hex,
        vertices=verts,
        indices=indices
        # Normals undefined for line
    )

def tessellate_surface(surface: Surface, u_segs: int = 10, v_segs: int = 10) -> Mesh:
    """Converts surface to a triangle grid Mesh."""
    import uuid
    verts = []
    uvs = []
    indices = []
    
    from engines.scene_engine.core.geometry import UV
    
    # Grid points
    for i in range(u_segs + 1):
        u = i / float(u_segs)
        for j in range(v_segs + 1):
            v = j / float(v_segs)
            
            pos = evaluate_surface(surface, u, v)
            verts.append(pos)
            uvs.append(UV(u=u, v=v))
            
    # Triangles
    # Grid width = v_segs + 1
    row_len = v_segs + 1
    
    for i in range(u_segs):
        for j in range(v_segs):
            # Quad: (i,j), (i, j+1), (i+1, j+1), (i+1, j)
            # p0 -- p1
            # |     |
            # p3 -- p2 (Counter?? No.)
            #
            # i is U (rows?), j is V (cols?)
            # Let's say i is row index, j is col index in `verts` array logic?
            # Index = i * row_len + j
            
            idx0 = i * row_len + j
            idx1 = i * row_len + (j + 1)
            idx2 = (i + 1) * row_len + (j + 1)
            idx3 = (i + 1) * row_len + j
            
            # Tri 1: 0-1-2? Depends on winding order.
            # Assuming CCW?
            indices.extend([idx0, idx1, idx2])
            indices.extend([idx0, idx2, idx3])
            
    # Calc normals logic? 
    # Use mesh ops recompute!
    # But for now return raw.
    
    return Mesh(
        id=uuid.uuid4().hex,
        vertices=verts,
        uvs=uvs,
        indices=indices
    )
