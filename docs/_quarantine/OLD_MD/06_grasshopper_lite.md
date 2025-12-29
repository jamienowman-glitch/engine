# Phase 6 – Param Graph v2 (Grasshopper-Style)

**Goal:**  
Expand the param system into a more powerful data-flow graph, with collections and a richer node library (early Grasshopper).

**Prompt:**
Build on Phase 2.

**Features:**
- Extend node types to handle lists/arrays.
- Add utility nodes: `RandomFloat`, `Noise`, `ScatterOnSurface`, `TransformPoints`.
- Introduce grouping constructs so nodes can output and accept arrays.
- Add `time` as a possible input.

**Evaluator:**
Upgrade the evaluator to handle collections (map operations).

**Examples:**
Create a couple of example nodes that produce point grids or scatter objects on a mesh surface.

**Tests:**
Update tests to cover list inputs/outputs and ensure cycles are detected gracefully.

**Constraint:**
Don’t worry about a visual editor; this is purely backend.
