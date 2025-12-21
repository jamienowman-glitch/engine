1. Goal  
Integrate image/vector/typography outputs into media_v2 with export presets and documented end-to-end flows for Photoshop/Illustrator-lite usage and reuse in video.

North star + Definition of Done  
- North star slice: Integrated exports—workers can render compositions (raster/vector/text), register artifacts with presets, and reuse them across image/video flows.  
- Definition of Done:  
  - media_v2 artifact kinds/meta for image/vector/text renders/compositions are defined and validated; deterministic filenames/prefixes.  
  - Export presets (web/social/print) for PNG/WEBP/JPEG with size/quality settings; services register artifacts with meta (preset_id, width/height, color profile).  
  - Combined flows (text + vector + raster) documented; examples show artifact lineage and reuse in video.  
  - Tests cover artifact validation, preset application, and meta correctness.

2. Scope (In / Out)  
- In: media_v2 artifact kinds/meta for image/vector/text renders/compositions, export profiles/presets, cross-engine glue (image_core/vector_core/typography_core) via docs/examples.  
- Out: UI/auth/tenant/safety, video/audio logic, orchestration.

3. Modules to touch  
- engines/media_v2/models.py  
- engines/media_v2/tests/test_media_v2_endpoints.py  
- engines/image_core/service.py  
- engines/image_core/backend.py  
- engines/image_core/tests (add/extend for export presets)  
- engines/vector_core/service.py (only if export handling changes)  
- engines/vector_core/tests/test_i04_vector.py (only if export handling changes)  
- engines/typography_core/service.py (only if registering text renders)  
- engines/typography_core/tests/test_i03_typography.py (only if service changes)  
- docs/engines/media_program/PHASE_I05_integration_and_presets.md  
- docs/engines/ENGINE_INVENTORY.md (artifact kinds)  
- READ-ONLY context: other files.  
STOP RULE: If you believe any file outside this list must be changed to complete this phase, stop and return a report instead of editing it.

4. Implementation checklist  
- Artifact kinds/meta (media_v2/models.py)  
  - Define/register artifact kinds for image compositions/renders, vector scenes/renders, text renders; meta includes preset_id, width/height, format, color_profile; enforce tenant/env and key prefix.  
  - Add validation/tests for new kinds; mark CONTRACT CHANGE if schema expands.  
- Export presets (image_core/backend.py/service.py)  
  - Add export presets: web_small/web_medium (WEBP/PNG), social_1080p, print_300dpi; include deterministic file naming pattern; clamp sizes/quality.  
  - **Supported presets:**  
    - `web_small`: WEBP, width 640, quality 75 ✅  
    - `web_medium`: WEBP, width 1280, quality 85 ✅  
    - `social_1080p`: PNG, width 1920, height 1080 ✅  
    - `print_300dpi`: JPEG, width 3000, height 3000, quality 95 ✅  
  - Ensure service registers artifacts with meta (preset_id, format, dimensions, color_profile).  
- Vector/typography export (vector_core/typography_core service.py)  
  - Ensure vector/text exports can be registered with preset meta when requested; keep backward compatibility.  
- Combined flow guidance  
  - Document how to combine raster/text/vector layers into a composition and register output artifacts; describe lineage expectations.  
- Validation & safety  
  - Reject missing tenant/env; enforce prefix `tenants/{tenant}/{env}/media_v2/...`; no prod temp fallback.  
- If additional files appear to need changes, STOP and report; do not refactor outside the modules listed in Modules to touch.

5. Tests  
- engines/media_v2/tests/test_media_v2_endpoints.py: new artifact kinds validation/meta; prefix enforcement.  
- engines/image_core/tests: export presets produce expected formats/meta and register artifacts (add/extend as needed).  
- engines/vector_core/tests/test_i04_vector.py: vector export round-trip and artifact registration if handled.  
- engines/typography_core/tests/test_i03_typography.py: text render artifact registration/meta if handled.  
Additional required cases:  
- Deterministic filenames/meta for presets; repeated export with same content+preset yields same cache key (if implemented).  
- Negative tests for unknown preset_id or missing tenant/env.  
- Color profile/format asserted in meta when presets applied.

6. Docs & examples  
- Update this phase doc with preset tables, artifact schema, and example flows.  
- Update ENGINE_INVENTORY/REGISTRY to list new artifact kinds.  
- Add end-to-end examples/diagrams: composition (raster+text+vector) → render with preset X → media_v2 artifacts → reuse in video overlay.  
- Provide example API walkthrough: create composition → POST render with preset → get artifact_id/uri → use in downstream flow.

7. Guardrails for implementers  
- Do not touch any auth/tenant/RequestContext/strategy lock/firearms/budget/safety code.  
- Do not touch any /ui, /core, or /tunes directories.  
- Do not modify any connectors, orchestration flows, manifests, or Nexus/agent behaviour; this phase is engines-only muscle.  
- Do not add or change any vector store / memory / logging pipelines; only use existing helpers in modules listed above.  
- If you need a new artifact kind or model field, mark CONTRACT CHANGE in this doc and only update media_v2/models.py and media_v2/tests/test_media_v2_endpoints.py as listed.  
- If additional files appear necessary, STOP and report instead of editing outside the allow-list.  
- Within the allow-list, implement all code/tests/docs to reach the Definition of Done; no TODOs unless a blocking external dependency is documented.

8. Execution note  
Complete this phase (code+tests+docs) strictly within the allow-listed files; if anything outside seems required, stop and report. Within the allow-list, deliver full Definition of Done with passing tests. This finishes the image/vector/type lane; proceed to the next lane unless a TODO – HUMAN DECISION REQUIRED truly blocks you.
