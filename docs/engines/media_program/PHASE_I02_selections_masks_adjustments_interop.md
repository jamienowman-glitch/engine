1. Goal  
Add selections/brush/polygon masks with feathering and ensure outputs interoperate with video masks/regions for Photoshop-lite compositions.

North star + Definition of Done  
- North star slice: Photoshop-lite selections/masks that can be reused across image/video—polygon/lasso/brush masks with feathering, registered as artifacts, consumable by image_core and video_mask/render.  
- Definition of Done:  
  - Selection tools (polygon/lasso/brush) rasterize deterministically with feathering; masks can be applied per-layer and exported as artifacts.  
  - Mask artifacts (`mask` kind) validated, tenant/env enforced, reusable in video flows; compatibility documented.  
  - Tests verify rasterization, feathering, mask application, idempotent generation, and interop with video_mask/render.

2. Scope (In / Out)  
- In: image_core selections/masks, media_v2 mask artifact meta, interoperability with video_mask/video_render mask consumption.  
- Out: vector/text features, auth/tenant/safety, UI/orchestration.

3. Modules to touch  
- engines/image_core/models.py  
- engines/image_core/selections.py  
- engines/image_core/backend.py  
- engines/image_core/service.py  
- engines/image_core/tests/test_i02_masks.py  
- engines/image_core/tests/test_i01_composite.py (only if mask application changes)  
- engines/video_mask/service.py (only if accepting/consuming new mask artifacts)  
- engines/video_mask/routes.py (only if accepting/consuming new mask artifacts)  
- engines/video_mask/tests/test_video_mask_endpoints.py (only if service/routes change)  
- engines/media_v2/models.py (mask artifact meta/schema if updated)  
- engines/media_v2/tests/test_media_v2_endpoints.py (only if artifact meta changes)  
- docs/engines/media_program/PHASE_I02_selections_masks_adjustments_interop.md  
- docs/engines/video_audio_atomic_design.md (mask interop notes only)  
- READ-ONLY context: other files.  
STOP RULE: If you believe any file outside this list must be changed to complete this phase, stop and return a report instead of editing it.

4. Implementation checklist  
- Design & contracts  
  - Define selection models (polygon/lasso points, brush strokes with width/opacity, feather radius) in models.py/selections.py.  
  - Ensure media_v2 `mask` artifact kind meta includes width/height/feather and tenant/env validation.  
- Selection rasterization (selections.py, backend.py)  
  - Implement deterministic rasterization for polygon/lasso/brush with feathering/anti-alias; fixed seeds for tests.  
  - Add selection hash for idempotent mask generation (optional) to avoid duplicates.  
- Mask application (backend.py, service.py)  
  - Apply masks per-layer using composition coordinates; support mask_artifact_id resolution via media_v2; validate dimensions/tenant/env.  
  - Export masks as artifacts with key prefix `tenants/{tenant}/{env}/...`; no prod temp fallback.  
- Interop with video (video_mask/service.py, routes.py if touched)  
  - Ensure video_mask can accept mask artifacts created here; validate tenant/env and asset linkage; preserve backward compatibility.  
- Validation & safety  
  - Reject invalid selections (too few points, oversized brush), missing tenant/env; clear errors.  
  - Clamp feather/brush width to sensible limits.  
- Fixtures  
  - Add sample selections for tests; ensure determinism across runs.  
- If additional files appear to need changes, STOP and report; do not refactor outside the modules listed in Modules to touch.

5. Tests  
- engines/image_core/tests/test_i02_masks.py: polygon/brush rasterization, feathering, mask artifact registration, validation errors.  
- engines/image_core/tests/test_i01_composite.py: per-layer mask application correctness (inline selection and artifact).  
- engines/video_mask/tests/test_video_mask_endpoints.py: consuming new mask artifacts remains functional; tenant/env enforcement if routes touched.  
- engines/media_v2/tests/test_media_v2_endpoints.py: mask artifact meta validation if schema touched.  
Additional required cases:  
- Idempotency test if selection hash added (same selection -> same mask).  
- Negative tests for invalid selection inputs and missing tenant/env.

6. Docs & examples  
- Update this phase doc with selection/mask API, artifact formats, and interop expectations with video.  
- Update ENGINE_INVENTORY/REGISTRY if mask meta schema changes.  
- Note mask compatibility in video_audio_atomic_design.md.  
- Add example: create polygon mask on an image, register mask artifact, apply to a layer, and reuse in video render for blur.

7. Guardrails for implementers  
- Do not touch any auth/tenant/RequestContext/strategy lock/firearms/budget/safety code.  
- Do not touch any /ui, /core, or /tunes directories.  
- Do not modify any connectors, orchestration flows, manifests, or Nexus/agent behaviour; this phase is engines-only muscle.  
- Do not add or change any vector store / memory / logging pipelines; only use existing helpers in modules listed above.  
- If mask kind/schema changes, mark CONTRACT CHANGE in this doc and only update media_v2/models.py and media_v2/tests/test_media_v2_endpoints.py as listed; update video_mask/render only if listed.  
- Keep public HTTP signatures stable; if additional files appear necessary, STOP and report instead of editing outside the allow-list.  
- Within the allow-list, implement all code/tests/docs to reach the Definition of Done; no TODOs unless a blocking external dependency is documented.

8. Execution note  
Complete this phase (code+tests+docs) strictly within the allow-listed files; if anything outside seems required, stop and report. Within the allow-list, deliver full Definition of Done with passing tests. Then proceed to PHASE_I03 unless blocked by TODO – HUMAN DECISION REQUIRED.
