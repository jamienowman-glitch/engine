
import pytest
import math
from engines.scene_engine.sketch.models import (
    Sketch, SketchPoint, SketchLine, SketchConstraint, SketchConstraintKind
)
from engines.scene_engine.sketch.solver import solve_sketch

def _dist(p1, p2):
    return math.sqrt((p2.x - p1.x)**2 + (p2.y - p1.y)**2)

def test_distance_constraint():
    # Line 0,0 -> 2,0. Constrain to length 4.
    p1 = SketchPoint(id="p1", x=0, y=0)
    p2 = SketchPoint(id="p2", x=2, y=0)
    line = SketchLine(id="l1", start_point_id="p1", end_point_id="p2")
    
    sketch = Sketch(
        id="s1",
        points=[p1, p2],
        lines=[line],
        constraints=[
            SketchConstraint(
                id="c1",
                kind=SketchConstraintKind.DISTANCE,
                entity_ids=["l1"],
                value=4.0
            )
        ]
    )
    
    solved = solve_sketch(sketch)
    
    # Expect 0,0 -> 2,0 center is 1,0.
    # New length 4. Center stays 1,0 usually (symmetric expansion).
    # Ends should be -1,0 and 3,0? Or similar.
    
    d = _dist(solved.points[0], solved.points[1])
    assert abs(d - 4.0) < 1e-3

def test_triangle_closure():
    # 3 Lines, unconnected initially.
    # L1: (0,0)->(1,0)
    # L2: (1,1)->(2,1)
    # L3: (0,1)->(0,2)
    # Coincident constraints to close loops.
    
    pts = [
        SketchPoint(id="p1a", x=0, y=0), SketchPoint(id="p1b", x=1, y=0), # L1
        SketchPoint(id="p2a", x=1, y=1), SketchPoint(id="p2b", x=2, y=1), # L2
        SketchPoint(id="p3a", x=0, y=1), SketchPoint(id="p3b", x=0, y=2) # L3
    ]
    
    # Coincident: p1b=p2a, p2b=p3a, p3b=p1a
    constraints = [
        SketchConstraint(id="c1", kind=SketchConstraintKind.COINCIDENT, entity_ids=["p1b", "p2a"]),
        SketchConstraint(id="c2", kind=SketchConstraintKind.COINCIDENT, entity_ids=["p2b", "p3a"]),
        SketchConstraint(id="c3", kind=SketchConstraintKind.COINCIDENT, entity_ids=["p3b", "p1a"]),
    ]
    
    sketch = Sketch(id="tri", points=pts, constraints=constraints)
    
    solved = solve_sketch(sketch)
    
    # Check distances between coincident pairs are 0
    pmap = {p.id: p for p in solved.points}
    
    assert _dist(pmap["p1b"], pmap["p2a"]) < 1e-4
    assert _dist(pmap["p2b"], pmap["p3a"]) < 1e-4
    assert _dist(pmap["p3b"], pmap["p1a"]) < 1e-4

def test_vertical_constraint():
    p1 = SketchPoint(id="p1", x=0, y=0)
    p2 = SketchPoint(id="p2", x=2, y=5)
    
    # Constrain vertical -> X should match
    c = SketchConstraint(id="c1", kind=SketchConstraintKind.VERTICAL, entity_ids=["p1", "p2"])
    
    sketch = Sketch(id="v", points=[p1, p2], constraints=[c])
    
    solve_sketch(sketch)
    
    assert abs(p1.x - p2.x) < 1e-4
