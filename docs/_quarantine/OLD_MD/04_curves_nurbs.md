# Phase 4 – Curves, Surfaces & NURBS Core v1

**Goal:**  
Introduce curve and surface primitives (Bézier, NURBS) and basic evaluation/tessellation functions.

**Prompt:**
In `engines/scene_engine/curves/`, add models for:
- `Polyline`
- `BezierCurve`
- `NURBSCurve`
- `NURBSSurface` (with knot vectors, control points, and weights).

**Logic:**
Implement evaluators:
- `point_at(t)` for curves.
- `point_at(u,v)` for surfaces.
- Tangent/normal computation.
- A simple tessellator that outputs a `Mesh` from curves/surfaces with a configurable subdivision count.

**Tests:**
Provide unit tests in `tests/test_curves_nurbs.py` verifying that evaluation matches known control-point values and tessellation produces reasonable vertex counts for simple examples (e.g. a quarter-circle).

**Constraint:**
Do not tackle boolean ops or CAD import/export here—this is the math core only.
