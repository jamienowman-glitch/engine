"""Sketch Constraint Solver (Relaxation)."""
from __future__ import annotations

import math
from typing import Dict, List, Tuple
from engines.scene_engine.core.geometry import Vector3
from engines.scene_engine.sketch.models import (
    Sketch, SketchConstraint, SketchConstraintKind, 
    SketchEntityKind, SketchPoint, SketchLine
)

MAX_ITERATIONS = 50
CONVERGENCE_EPSILON = 1e-4

def _vec(p: SketchPoint) -> Vector3:
    return Vector3(x=p.x, y=p.y, z=0)

def _dist(p1: SketchPoint, p2: SketchPoint) -> float:
    dx = p2.x - p1.x
    dy = p2.y - p1.y
    return math.sqrt(dx*dx + dy*dy)

def _solve_distance(p1: SketchPoint, p2: SketchPoint, target: float):
    """Moves p1, p2 to satisfy target distance."""
    current = _dist(p1, p2)
    if current < 1e-6:
        # Coincident points, can't solve direction. Move p2 arbitrarily?
        p2.x += 0.01
        current = _dist(p1, p2)
    
    diff = current - target
    if abs(diff) < CONVERGENCE_EPSILON:
        return
        
    # Adjustment ratio
    # We want to move each point half the error distance along the vector
    # Vector P1->P2
    vx = (p2.x - p1.x) / current
    vy = (p2.y - p1.y) / current
    
    delta = diff * 0.5
    
    p1.x += vx * delta
    p1.y += vy * delta
    
    p2.x -= vx * delta
    p2.y -= vy * delta

def _solve_coincident(p1: SketchPoint, p2: SketchPoint):
    """Averages p1 and p2."""
    mid_x = (p1.x + p2.x) * 0.5
    mid_y = (p1.y + p2.y) * 0.5
    
    p1.x = mid_x
    p1.y = mid_y
    p2.x = mid_x
    p2.y = mid_y

def _solve_vertical(p1: SketchPoint, p2: SketchPoint):
    """Aligns X."""
    mid_x = (p1.x + p2.x) * 0.5
    p1.x = mid_x
    p2.x = mid_x

def _solve_horizontal(p1: SketchPoint, p2: SketchPoint):
    """Aligns Y."""
    mid_y = (p1.y + p2.y) * 0.5
    p1.y = mid_y
    p2.y = mid_y

def solve_sketch(sketch: Sketch) -> Sketch:
    """Iteratively solves constraints."""
    
    # Map ID -> Object for fast lookups
    # Note: solver modifies points IN PLACE.
    # We should modify the sketch object passed in (it's mutable Pydantic model at runtime usually)
    # or copy. Pydantic defaults to mutable.
    
    points_map = {p.id: p for p in sketch.points}
    lines_map = {l.id: l for l in sketch.lines}
    
    def get_points(entity_id: str) -> List[SketchPoint]:
        # Return points associated with entity
        # If Point: [p]
        # If Line: [start, end]
        if entity_id in points_map:
            return [points_map[entity_id]]
        if entity_id in lines_map:
            l = lines_map[entity_id]
            return [points_map[l.start_point_id], points_map[l.end_point_id]]
        return []

    for _ in range(MAX_ITERATIONS):
        max_error = 0.0
        
        for c in sketch.constraints:
            
            # Distance
            if c.kind == SketchConstraintKind.DISTANCE:
                # Expects 1 Line, or 2 Points.
                pts = []
                for eid in c.entity_ids:
                    pts.extend(get_points(eid))
                
                # If we have 2 points total (1 line gives 2 pts)
                # If we selected 2 points directly, we have 2 pts.
                # If we selected 2 lines... invalid.
                
                if len(pts) == 2:
                    p1, p2 = pts[0], pts[1]
                    target = c.value if c.value is not None else _dist(p1, p2)
                    
                    err = abs(_dist(p1, p2) - target)
                    max_error = max(max_error, err)
                    
                    _solve_distance(p1, p2, target)

            # Coincident
            elif c.kind == SketchConstraintKind.COINCIDENT:
                # Expects 2 Points (or end of line + point)
                # Just flatten all points involved
                pts = []
                for eid in c.entity_ids:
                    pts.extend(get_points(eid))
                    
                # Pairwise average? Or average all to centroid.
                if len(pts) >= 2:
                    cx = sum(p.x for p in pts) / len(pts)
                    cy = sum(p.y for p in pts) / len(pts)
                    
                    for p in pts:
                        dist_sq = (p.x - cx)**2 + (p.y - cy)**2
                        max_error = max(max_error, math.sqrt(dist_sq))
                        p.x = cx
                        p.y = cy

            # Horizontal / Vertical
            elif c.kind in (SketchConstraintKind.HORIZONTAL, SketchConstraintKind.VERTICAL):
                pts = []
                for eid in c.entity_ids:
                    pts.extend(get_points(eid))
                    
                # Usually applied to a Line (2 pts) or 2 Points.
                if len(pts) == 2:
                    p1, p2 = pts[0], pts[1]
                    if c.kind == SketchConstraintKind.VERTICAL:
                        err = abs(p1.x - p2.x)
                        max_error = max(max_error, err)
                        _solve_vertical(p1, p2)
                    else:
                        err = abs(p1.y - p2.y)
                        max_error = max(max_error, err)
                        _solve_horizontal(p1, p2)
            
            # Equal Length
            elif c.kind == SketchConstraintKind.EQUAL_LENGTH:
                 # Expects 2 Lines -> 4 points.
                 # L1 (p1, p2), L2 (p3, p4)
                 # Target = Average(L1, L2)?
                 if len(c.entity_ids) == 2:
                     # Assume they are lines
                     pts1 = get_points(c.entity_ids[0])
                     pts2 = get_points(c.entity_ids[1])
                     
                     if len(pts1) == 2 and len(pts2) == 2:
                         d1 = _dist(pts1[0], pts1[1])
                         d2 = _dist(pts2[0], pts2[1])
                         
                         avg = (d1 + d2) * 0.5
                         err = abs(d1 - d2)
                         max_error = max(max_error, err)
                         
                         _solve_distance(pts1[0], pts1[1], avg)
                         _solve_distance(pts2[0], pts2[1], avg)

        if max_error < CONVERGENCE_EPSILON:
             break
             
    return sketch
