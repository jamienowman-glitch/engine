# Phase 5 – Sketch & Dimensional Constraints v1

**Goal:**  
Add a 2D sketch system with basic dimensional constraints (distances, angles, parallel/perpendicular).

**Prompt:**
Create `engines/scene_engine/sketch/` with entities for `SketchPoint`, `SketchLine`, `SketchArc`, and a `Sketch` that holds them. 

**Constraints:**
Introduce constraint models for `DistanceConstraint`, `AngleConstraint`, `ParallelConstraint`, and `PerpendicularConstraint`, each referencing the relevant sketch entities.

**Solver:**
Implement a simple solver that adjusts point positions iteratively to satisfy constraints.

**3D Embedding:**
Provide a way to embed a sketch in 3D via a transform (local plane attached to a `SceneNodeV2`).

**Tests:**
Tests in `tests/test_sketch_constraints.py` should:
- Create a small sketch (e.g. triangle with equal sides).
- Verify that constraints converge to expected lengths/angles.
- Avoid full CAD-grade stability; aim for basic functionality.
