1. Goal  
Make avatar rigs correct and extensible: solid auto-rigs, morph targets, retarget hooks, and validation of skeletons to form the foundation of an avatar builder.

North star + Definition of Done  
- North star slice: ReadyPlayerMe/game-ready rig baseline—validated humanoid rigs with morph targets and retarget hooks.  
- Definition of Done:  
  - Auto-rig produces a validated skeleton (bone counts/naming/orientation) with deterministic output; rig validation routine catches errors.  
  - Morph targets stored/applicable with predictable vertex deltas; retarget mapping strategy documented/implemented.  
  - Tests cover rig integrity, morph apply, and deterministic retarget mapping.

2. Scope (In / Out)  
- In: Rig generation/validation, morph target schema/apply, retargeting scaffolds.  
- Out: UI/auth/tenant/safety, animation library breadth (later), materials/kits (later), orchestration.

3. Modules to touch  
- engines/scene_engine/avatar/*  
- engines/scene_engine/tests/test_avatar_*.py  
- engines/scene_engine/tests/test_mesh_ops.py (only if morph storage affects mesh ops)  
- engines/animation_kernel/service.py  
- engines/animation_kernel/ik_solver.py (if IK validation needed)  
- engines/animation_kernel/tests/test_anim_basic.py  
- engines/animation_kernel/tests/test_ik.py  
- engines/mesh_kernel/service.py (only if morph storage helpers needed)  
- engines/mesh_kernel/tests/test_mesh_basic.py (only if morph storage changes)  
- docs/engines/geometry_cad_program/PHASE_AV01_rig_and_morph_foundations.md  
- docs/engines/ENGINE_INVENTORY.md (only if schema references change)  
- READ-ONLY context: other files.  
STOP RULE: If you believe any file outside this list must be changed to complete this phase, stop and return a report instead of editing it.

4. Implementation checklist  
- Design & schemas  
  - Define/confirm rig schema: required bones, naming, orientation, hierarchy; add validation routine producing clear errors.  
  - Define morph target/blendshape model: vertex delta storage, id, applicable meshes, meta (version).  
  - Document retarget mapping convention (e.g., humanoid mapping) and version it.  
- Rig generation & validation (scene_engine/avatar, animation_kernel)  
  - Update auto-rig to emit deterministic skeleton with expected naming; include root orientation/unit scale checks.  
  - Add validate_rig entrypoint to run schema checks and report missing/misaligned bones.  
  - Ensure IK solver respects validated bones; add guards for invalid input.  
- Morph targets (mesh_kernel/service.py if needed, scene_engine/avatar)  
  - Store morph targets per mesh; apply_morph service to apply weighted deltas deterministically.  
  - Tag morph application in history/meta for downstream export.  
- Retarget hooks (animation_kernel/service.py)  
  - Implement mapping from source rig -> target rig using naming/TPose alignment; deterministic mapping with default convention; allow overrides.  
  - Surface meta (mapping version, source/target ids).  
- Validation & safety  
  - Reject NaNs/non-unit scales; ensure transforms are normalized; clear errors on invalid rigs/morphs.  
- If additional files appear to need changes, STOP and report; do not refactor outside the modules listed in Modules to touch.

5. Tests  
- engines/animation_kernel/tests/test_anim_basic.py & test_ik.py: auto_rig bone count/name validation; retarget mapping determinism; IK input validation.  
- engines/scene_engine/tests/test_avatar_*.py: morph apply changes vertices predictably; rig validation passes/fails appropriately; metadata written.  
- engines/mesh_kernel/tests/test_mesh_basic.py: morph storage/apply round-trip if touched.  
Additional required cases:  
- Determinism: same input -> same rig/morph results.  
- Negative tests for missing required bones, invalid morph deltas.  
- Retarget mapping produces consistent results for same source/target rigs.

6. Docs & examples  
- Update this phase doc with rig schema, morph target description, retarget mapping rules/defaults.  
- Update ENGINE_INVENTORY if schema references change.  
- Add example: create base avatar with default rig, apply morph “smile”, run validate_rig, retarget from source rig to target rig with documented mapping.

7. Guardrails for implementers  
- Do not touch any auth/tenant/RequestContext/strategy lock/firearms/budget/safety code.  
- Do not touch any /ui, /core, or /tunes directories.  
- Do not modify any connectors, orchestration flows, manifests, or Nexus/agent behaviour; this phase is engines-only muscle.  
- Do not add or change any vector store / memory / logging pipelines; only use existing helpers in modules listed above.  
- If you need a new artifact kind or model field, mark CONTRACT CHANGE in this doc and only update explicitly listed files/tests.  
- If additional files appear necessary, STOP and report instead of editing outside the allow-list.  
- Within the allow-list, implement all code/tests/docs to reach the Definition of Done; no TODOs unless a blocking external dependency is documented.

8. Execution note  
Complete this phase (code+tests+docs) strictly within the allow-listed files; if anything outside seems required, stop and report. Deliver full Definition of Done with passing tests. Then proceed to PHASE_AV02 unless a TODO – HUMAN DECISION REQUIRED truly blocks you.
