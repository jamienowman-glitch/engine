1. Goal  
Add vector scenegraph: shapes/paths/strokes/fills, transforms, boolean ops, and SVG import/export with rasterization into image_core for Illustrator-lite needs.

North star + Definition of Done  
- North star slice: Illustrator-lite vector primitives/SVG—paths, groups, boolean ops, basic transforms, and SVG round-trip usable for icons/overlays, rasterized deterministically into image layers.  
- Definition of Done:  
  - vector_core defines nodes (Rect/Circle/Path/Group) with styles/transforms, supports boolean ops where deps allow, and imports/exports a defined SVG subset.  
  - Rasterization produces deterministic images (AA) for use in image_core layers with masks/blends; serialization/deserialization supported.  
  - Tests cover primitives, transforms, boolean ops (skip if dependency absent), SVG round-trip, and raster alignment.

2. Scope (In / Out)  
- In: vector_core engine, SVG import/export subset, rasterization into image_core vector layers.  
- Out: UI/auth/tenant/safety, advanced CAD features, vector animation, orchestration.

3. Modules to touch  
- engines/vector_core/models.py  
- engines/vector_core/renderer.py  
- engines/vector_core/svg_parser.py (or importer/exporter files)  
- engines/vector_core/service.py (if present)  
- engines/vector_core/tests/test_i04_vector.py  
- engines/image_core/backend.py (vector layer rasterization only)  
- engines/image_core/tests/test_i01_composite.py (only if vector layer rendering changes)  
- docs/engines/media_program/PHASE_I04_vector_primitives_svg.md  
- docs/engines/ENGINE_INVENTORY.md (only if new artifact kinds added)  
- READ-ONLY context: other files.  
STOP RULE: If you believe any file outside this list must be changed to complete this phase, stop and return a report instead of editing it.

4. Implementation checklist  
- Design & models  
  - Define vector node model (Group/Rect/Circle/Path) with style (fill/stroke/stroke_width/opacity/gradient stubs) and transforms (translate/scale/rotate).  
  - Add boolean ops support (union/subtract/intersect) on paths if dependency available; mark NOT_IMPLEMENTED with meta flag if absent.  
- SVG import/export (svg_parser.py)  
  - Implement subset import/export for rect/circle/path/group/styles/transforms; preserve IDs/styles; handle viewport size; round-trip tests.  
- Rasterization (renderer.py, image_core/backend.py)  
  - Rasterize vector scenes with AA using Pillow or agg; deterministic ordering and transform application; expose width/height overrides.  
  - Integrate rasterized vector layers into image_core; support opacity/blend/masks; serialize/deseriaize vector scenes for edits.  
- Validation & safety  
  - Clamp stroke widths; reject invalid paths; clear errors on unsupported SVG features; deterministic outputs.  
- Optional artifacts  
  - If vector scenes are registered, ensure artifact meta/version recorded; tag CONTRACT CHANGE if adding kinds.  
- Docs sync  
  - Document supported SVG features, boolean ops behavior (or lack), and rasterization pipeline in this doc.  
- If additional files appear to need changes, STOP and report; do not refactor outside the modules listed in Modules to touch.

5. Tests  
- engines/vector_core/tests/test_i04_vector.py: primitive creation, transforms, SVG round-trip, rasterization alignment.  
- Add boolean ops tests (skip if dependency missing) with deterministic outputs.  
- image_core integration test: vector layer renders correctly with blend/mask.  
Additional required cases:  
- Import/export tests for unsupported SVG features to ensure graceful fallback/warnings.  
- Determinism: same vector scene -> same raster output hash.

6. Docs & examples  
- Update this phase doc with vector model, supported SVG features, boolean ops behavior, rasterization pipeline, and example requests.  
- Update ENGINE_INVENTORY/REGISTRY if new artifact kinds (vector_scene) added.  
- Add example: import SVG icon -> rasterize into image layer with blend mode screen -> render composition.

7. Guardrails for implementers  
- Do not touch any auth/tenant/RequestContext/strategy lock/firearms/budget/safety code.  
- Do not touch any /ui, /core, or /tunes directories.  
- Do not modify any connectors, orchestration flows, manifests, or Nexus/agent behaviour; this phase is engines-only muscle.  
- Do not add or change any vector store / memory / logging pipelines; only use existing helpers in modules listed above.  
- If composition model changes, mark CONTRACT CHANGE in this doc and update only explicitly listed files/tests.  
- If additional files appear necessary, STOP and report instead of editing outside the allow-list.  
- Within the allow-list, implement all code/tests/docs to reach the Definition of Done; no TODOs unless a blocking external dependency is documented.

8. Execution note  
Complete this phase (code+tests+docs) strictly within the allow-listed files; if anything outside seems required, stop and report. Within the allow-list, deliver full Definition of Done with passing tests. Then proceed to PHASE_I05 unless a TODO – HUMAN DECISION REQUIRED truly blocks you.
