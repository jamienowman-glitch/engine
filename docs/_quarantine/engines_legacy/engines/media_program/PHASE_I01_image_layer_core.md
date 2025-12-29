1. Goal  
Stand up an image layer stack: layers, blend modes, adjustments/filters, masks, and deterministic render/export for Photoshop-lite compositions.

North star + Definition of Done  
- North star slice: Photoshop-lite for social graphics/thumbnails—real layer stack (raster, text, vector), blend modes, basic adjustments, masks reusable as artifacts.  
- Definition of Done:  
  - image_core supports compositions with ordered layers (raster/text/vector), blend modes, transforms, opacity, masks; adjustments (brightness/contrast/saturation/sharpness/gamma) and basic filters (blur/sharpen).  
  - Render/export produces deterministic PNG/WEBP artifacts via media_v2 with meta (width/height/layers_count).  
  - Mask artifacts (from selections or references) usable in-layer and interoperable with video masks; validations in place.  
  - Tests verify blends/adjustments/masks deterministically; docs include example flow (create comp → render).

2. Scope (In / Out)  
- In: image_core engine (models/backend/service), media_v2 artifact types for image renders/masks, optional routes if present.  
- Out: video/audio changes, UI/auth/tenant/safety, vector/text enhancements (later phases), orchestration.

3. Modules to touch  
- engines/image_core/models.py  
- engines/image_core/backend.py  
- engines/image_core/service.py  
- engines/image_core/tests/test_i01_composite.py  
- engines/image_core/tests/test_i02_masks.py (only if mask handling changes)  
- engines/media_v2/models.py (artifact kinds/schema/meta only)  
- engines/media_v2/tests/test_media_v2_endpoints.py (only if artifact kinds/meta change)  
- docs/engines/media_program/PHASE_I01_image_layer_core.md  
- docs/engines/ENGINE_INVENTORY.md (only if artifact kinds change)  
- READ-ONLY context: other files.  
STOP RULE: If you believe any file outside this list must be changed to complete this phase, stop and return a report instead of editing it.

4. Implementation checklist  
- Design & contracts  
  - Define composition model: layers ordered with type (raster/text/vector), transform (position/scale/rotation), opacity, blend_mode, mask (inline selection or artifact), adjustments (brightness/contrast/saturation/sharpness/gamma), filters (blur/sharpen).  
  - **Supported blend modes:** `normal`, `multiply`, `screen`, `overlay`, `darken`, `lighten`, `add`.  
  - **Supported adjustments/filters:** exposure, contrast, saturation, brightness, sharpness, gamma; filters: `blur` (Gaussian), `sharpen` (UnsharpMask-based).  
  - **Artifact schema/meta:** `image_render` artifacts should include `width`, `height`, `layers_count`, and `pipeline_hash` in `meta`. Masks use `mask` kind and include `width`, `height`, `selection_hash` and selection details.  
  - Extend media_v2 models with `image_render` (and confirm `mask`) artifact kinds; require tenant/env; meta fields include width, height, layers_count.  
- Backend/service (backend.py, service.py)  
  - Implement deterministic raster pipeline using Pillow (or OpenCV) with fixed resampling/DPI defaults.  
  - Apply adjustments/filters in defined order; support blend modes (normal/multiply/screen/overlay/darken/lighten/add) with mask-aware compositing.  
  - Support inline masks and mask_artifact_id; resolve mask artifacts via media_v2; enforce key prefix, reject missing tenant/env.  
  - Render/export to PNG/WEBP; register artifacts via media_v2 with meta; include composition hash for caching if added.  
- Validation & safety  
  - Clamp inputs (opacity 0–1, adjustments reasonable ranges); validate mask dimensions; reject missing tenant/env; no prod fallback to temp paths outside media_v2 patterns.  
- Caching/fixtures  
  - Optional: add composition hash for idempotent render reuse; ensure deterministic outputs across runs.  
  - Add small fixtures for layers/masks in tests.  
- If additional files appear to need changes, STOP and report; do not refactor outside the modules listed in Modules to touch.

5. Tests  
- engines/image_core/tests/test_i01_composite.py: blend modes, adjustments, opacity ordering, deterministic render hash/bytes for fixture composition.  
- engines/image_core/tests/test_i02_masks.py: mask application from inline selection/artifact; mask dimension validation; opacity interactions.  
- engines/media_v2/tests/test_media_v2_endpoints.py: artifact validation/meta if schema touched.  
Additional required cases:  
- Negative tests for invalid blend mode/opacity out of range → clear error.  
- Determinism: same comp -> identical output hash.  
- Mask artifact resolution with tenant/env enforced.

6. Docs & examples  
- Update this phase doc with supported blend modes/adjustments/filters, artifact schemas, and constraints.  
- Update ENGINE_INVENTORY if artifact kinds/meta change.  
- Add example: create composition with background + logo + text layer + mask; render PNG via service (or describe API if present) and register artifact.

7. Guardrails for implementers  
- Do not touch any auth/tenant/RequestContext/strategy lock/firearms/budget/safety code.  
- Do not touch any /ui, /core, or /tunes directories.  
- Do not modify any connectors, orchestration flows, manifests, or Nexus/agent behaviour; this phase is engines-only muscle.  
- Do not add or change any vector store / memory / logging pipelines; only use existing helpers in modules listed above.  
- If you need a new artifact kind or model field, mark CONTRACT CHANGE in this doc and only update media_v2/models.py and media_v2/tests/test_media_v2_endpoints.py as listed.  
- If additional files appear necessary, STOP and report instead of editing outside the allow-list.  
- Within the allow-list, implement all code/tests/docs to reach the Definition of Done; no TODOs unless a blocking external dependency is documented.

8. Execution note  
Complete this phase (code+tests+docs) strictly within the allow-listed files; if anything outside seems required, stop and report. Within the allow-list, deliver full Definition of Done with passing tests. Then proceed to PHASE_I02 unless blocked by a TODO – HUMAN DECISION REQUIRED.
