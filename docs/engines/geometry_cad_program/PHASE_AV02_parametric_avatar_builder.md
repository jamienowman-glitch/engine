1. Goal  
Expose parametric controls (sliders) for body/face/hair; presets; history/undo; deterministic avatar generation to build a ReadyPlayerMe-class avatar builder.

North star + Definition of Done  
- North star slice: Parametric avatar builder—workers can apply presets and sliders to body/face/hair, with deterministic seeding and undo/redo.  
- Definition of Done:  
  - AvatarParamSet schema with bounded sliders; preset library (male/female/child/stylized) and deterministic seed application.  
  - Params map to morphs/rig transforms deterministically; history/undo stack persists changes.  
  - Tests verify deterministic apply, preset coverage, bounds enforcement, and undo/redo.

2. Scope (In / Out)  
- In: Parameter schema, preset library, history stack, deterministic seeding.  
- Out: Rendering, materials, animations (later phases), UI/auth/tenant/safety.

3. Modules to touch  
- engines/scene_engine/params/*  
- engines/scene_engine/avatar/*  
- engines/scene_engine/store/history* (or equivalent history helpers)  
- engines/scene_engine/tests/test_params_avatar.py  
- engines/scene_engine/tests/test_avatar_*.py  
- engines/scene_engine/tests/test_scene_store.py (only if history persists)  
- docs/engines/geometry_cad_program/PHASE_AV02_parametric_avatar_builder.md  
- READ-ONLY context: other files.  
STOP RULE: If you believe any file outside this list must be changed to complete this phase, stop and return a report instead of editing it.

4. Implementation checklist  
- Design & presets  
  - Define AvatarParamSet with bounded sliders (body proportions, face dims, hair styles/options) and defaults; validate inputs/clamp safely.  
  - Build preset library (male/female/child/stylized) with deterministic seeds; loader to apply presets to param sets.  
- Param application (scene_engine/avatar/params)  
  - Map params to morph targets + rig transforms deterministically; apply explicit seed for repeatability; record meta.  
  - Ensure param->morph mappings documented and versioned.  
- History/undo (scene_engine/store/history*)  
  - Implement history/undo stack for param changes (push/pop) with max depth; store scene/rig state per step; deterministic ordering.  
  - Persist history entries if store exists; ensure redo behavior clear.  
- Validation & safety  
  - Enforce bounds; reject invalid params; clear errors; maintain backward compatibility.  
- If additional files appear to need changes, STOP and report; do not refactor outside the modules listed in Modules to touch.

5. Tests  
- engines/scene_engine/tests/test_params_avatar.py: applying params yields stable meshes/rig transforms given same seed; bounds enforcement errors; preset coverage.  
- engines/scene_engine/tests/test_avatar_*.py: presets load/apply without errors; deterministic outputs; history undo/redo restores prior state; max depth respected.  
- engines/scene_engine/tests/test_scene_store.py (if touched): history persistence.  
Additional required cases:  
- Determinism: same preset+seed -> same avatar output.  
- Negative tests for invalid slider values; preset missing raises clear error.

6. Docs & examples  
- Update this phase doc with param schema, preset list, seed/determinism rules, history behavior.  
- Add examples: apply “casual_male” preset, tweak face/height sliders, undo/redo, confirm deterministic mesh/rig.  
- Note any schema references in ENGINE_INVENTORY if applicable.

7. Guardrails for implementers  
- Do not touch any auth/tenant/RequestContext/strategy lock/firearms/budget/safety code.  
- Do not touch any /ui, /core, or /tunes directories.  
- Do not modify any connectors, orchestration flows, manifests, or Nexus/agent behaviour; this phase is engines-only muscle.  
- Do not add or change any vector store / memory / logging pipelines; only use existing helpers in modules listed above.  
- If you need a new artifact kind or model field, mark CONTRACT CHANGE in this doc and only update explicitly listed files/tests.  
- If additional files appear necessary, STOP and report instead of editing outside the allow-list.  
- Within the allow-list, implement all code/tests/docs to reach the Definition of Done; no TODOs unless a blocking external dependency is documented.

8. Execution note  
Complete this phase (code+tests+docs) strictly within the allow-listed files; if anything outside seems required, stop and report. Deliver full Definition of Done with passing tests. Then proceed to PHASE_AV03 unless a TODO – HUMAN DECISION REQUIRED truly blocks you.
