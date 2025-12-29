# Phase 2 – Param/Graph v1

**Goal:**  
Introduce a small parameter graph system so that a few sliders (e.g. energy, mood) can drive scene properties (pose, colours, camera distance).

**Prompt:**
You are working ONLY in northstar-engines. Do not touch tenants/auth, DB, or Haze.

**Models:** 
Create `engines/scene_engine/params/` with:
- `ParamType`
- `ParamValue`
- `ParamNodeKind`
- `ParamNode`
- `ParamGraph`
- A simple evaluator (`evaluate_param_graph`) supporting: CONSTANT, ADD, MULTIPLY, REMAP, CLAMP, VECTOR_COMPOSE, SCRIPT_EXPR nodes.

**Bindings:**
Add a small binding layer (`ParamTargetKind`, `ParamBinding`) and `apply_param_bindings` so a param output can drive:
- Node Y position
- Uniform scale
- Material colour
- Camera distance
- Avatar style field via `AvatarStyleParams`.

**BBK:** 
- Add `build_bbk_mc_param_graph()` to create a graph with energy, aggression, camera_in_out, mood sliders.
- Create `build_bbk_mc_parametric_scene()` that returns `(scene, graph)` and includes bindings to head/arm pose, camera distance and colour brightness.

**Tests:** 
Include unit tests for graph evaluation, bindings, and a simple BBK param scene that shows different results at energy=0 vs energy=1.
