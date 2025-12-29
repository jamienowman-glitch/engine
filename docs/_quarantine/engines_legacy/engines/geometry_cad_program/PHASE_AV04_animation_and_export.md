1. Goal  
Add motion library playback/blend, FK/IK mixer, and export avatar + animation to USD/GLTF deterministically for ReadyPlayerMe/game-ready usage.

Status Update (Dec 2025):
- Implemented: Motion library core (playback_at_time, blend_clips), FK/IK mixing with per-bone masks, chain IK solver with convergence improvements and deterministic behavior, export bindings now include `SceneV2.meta` extras, and deterministic export tests (JSON hash equality) were added.
- Tests added: IK convergence tests (colinear/unreachable/degenerate/random), FK/IK mask tests, export determinism and extras tests. All local AV04-related tests are passing.
- Remaining: Further harden chain IK for edge-case convergence across more geometries, add binary export hashing for GLTF/GLB, and finalize docs/examples in this phase doc (below).

North star + Definition of Done  
- North star slice: Avatar with motions—motion library, FK/IK mix, and clean GLTF/USD export including rig/morphs/materials/animations.  
- Definition of Done:  
  - Motion library schema (clip metadata, durations, bone tracks) with deterministic playback/blend.  
  - FK/IK mixer overlays IK corrections per bone mask; deterministic output.  
  - Export bundles rig + meshes + materials + morphs + animations to GLTF/USD with stable IDs/names; meta includes clip info.  
  - Tests verify playback/blend, FK/IK overlay, export contents, and determinism.

2. Scope (In / Out)  
- In: animation_kernel blending/FK-IK mix, motion library schema, scene_engine export pipeline for rigs/meshes/materials/morphs/animations.  
- Out: UI/auth/tenant/safety, real-time rendering/shaders.

3. Modules to touch  
- engines/animation_kernel/service.py  
- engines/animation_kernel/tests/test_anim_basic.py  
- engines/animation_kernel/tests/test_ik.py  
- engines/scene_engine/export/*  
- engines/scene_engine/tests/test_scene_export.py (or equivalent export tests)  
- engines/scene_engine/avatar/* (animation bindings)  
- engines/scene_engine/tests/test_avatar_*.py (only if animation bindings change)  
- docs/engines/geometry_cad_program/PHASE_AV04_animation_and_export.md  
- READ-ONLY context: other files.  
STOP RULE: If you believe any file outside this list must be changed to complete this phase, stop and return a report instead of editing it.

4. Implementation checklist  
- Motion library (animation_kernel/service.py)  
  - Define motion library schema (clip metadata: fps, duration, bone tracks, loop flags, action constants) with versioning.  
  - Implement playback at time t; add clip blending (crossfade/pose blend) deterministically.  
- FK/IK mixer  
  - Implement FK/IK mixing per bone mask; overlay IK corrections on FK animation; deterministic results for same inputs.  
  - Validate inputs (bone existence) and clear errors.  
- Animation bindings (scene_engine/avatar)  
  - Bind animations to avatar rigs generated earlier; validate bone name matches; fallback errors.  
  - Record animation meta (clip names, loop flags) on scene for export.  
- Export (scene_engine/export/*)  
  - Bundle rig + meshes + materials + morph targets + animation tracks into GLTF/USD; stable IDs/names.  
  - Include tangents/morph data; optional compression flag; add meta (clips included).  
  - Sanitize file names; include hash/version in meta for determinism.  
- Validation & safety  
  - Ensure coordinate system/unit consistency; reject missing rig/morph data; keep backward compatibility.  
- If additional files appear to need changes, STOP and report; do not refactor outside the modules listed in Modules to touch.

5. Tests  
- engines/animation_kernel/tests/test_anim_basic.py & test_ik.py: playback/blend correctness, FK/IK mixing per bone mask, determinism.  
- engines/scene_engine/tests/test_scene_export.py: GLTF/USD export contains rig/meshes/materials/morphs/animations; stable IDs; hash equality on repeat.  
- engines/scene_engine/tests/test_avatar_*.py: animation binding success/failure as needed.  
Additional required cases:  
- Negative tests for missing bones/invalid clip data.  
- Determinism: same inputs -> same export hash/IDs.  
- Optional: export round-trip checks for presence of animations/morph targets.

6. Docs & examples  
- Update this phase doc with motion library schema, FK/IK mixing rules, and export pipeline steps/formats.  
- Add export examples (paths/meta fields) in geometry_cad_program docs.  
- Example: apply “walk” clip + IK foot planting, then export GLTF with morphs/materials; verify deterministic IDs.

7. Guardrails for implementers  
- Do not touch any auth/tenant/RequestContext/strategy lock/firearms/budget/safety code.  
- Do not touch any /ui, /core, or /tunes directories.  
- Do not modify any connectors, orchestration flows, manifests, or Nexus/agent behaviour; this phase is engines-only muscle.  
- Do not add or change any vector store / memory / logging pipelines; only use existing helpers in modules listed above.  
- If you need a new artifact kind or model field, mark CONTRACT CHANGE in this doc and only update explicitly listed files/tests.  
- If additional files appear necessary, STOP and report instead of editing outside the allow-list.  
- Within the allow-list, implement all code/tests/docs to reach the Definition of Done; no TODOs unless a blocking external dependency is documented.

8. Execution note  
Complete this phase (code+tests+docs) strictly within the allow-listed files; if anything outside seems required, stop and report. Deliver full Definition of Done with passing tests. This finishes the avatar lane; proceed to next lane unless blocked by TODO – HUMAN DECISION REQUIRED.
