# Phase 3 – Mesh Ops & Geometry Tools v1

**Goal:**  
Provide basic mesh utilities and operations to clean and combine meshes, giving you tools beyond just primitives.

**Prompt:**
Stay within `scene_engine`.

**Module:**
Define a new module `engines/scene_engine/ops/mesh_ops.py` with functions for:
- Merging vertices that share position within a small epsilon.
- Recomputing normals.
- Recentering meshes.
- Scaling meshes.
- Combining multiple meshes into one (with correct index offsets).
- Provide simple voxel-based boolean approximations (union/diff/intersect) for low-poly meshes if it can be done without external C libraries.

**Helpers:**
Update or extend `geometry.py` with vector math helpers (add, subtract, dot) if not already present.

**Tests:**
Write tests in `tests/test_mesh_ops.py` validating each utility (e.g. merging reduces vertex count, normals recompute as expected).

**Constraint:**
Don’t integrate persistence or import/export here; keep it in-memory.
