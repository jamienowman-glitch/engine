1. Goal  
Build typography engine with variable font loading, shaping, layout, and raster export for Photoshop/Illustrator-lite overlays (titles/lower-thirds).

North star + Definition of Done  
- North star slice: Variable-font typography-lite for titles/lower-thirds—font registry, axis controls, wrapping/alignment, and raster/text artifacts usable in image/video overlays.  
- Definition of Done:  
  - typography_core loads variable fonts, supports axis overrides, shaping/wrapping/alignment, and renders text to images deterministically.  
  - text rendering integrates with video_text/image_core layers; artifacts (text renders) can be registered via media_v2 if needed.  
  - Tests verify layout, wrapping, axis handling, determinism; docs include registry guide and examples.

2. Scope (In / Out)  
- In: typography_core engine and font registry, integration into video_text and image_core text layers.  
- Out: vector path ops, auth/tenant/safety, UI/orchestration.

3. Modules to touch  
- engines/design/fonts/registry.py  
- engines/design/fonts/__init__.py (if needed for registry exports)  
- engines/typography_core/renderer.py  
- engines/typography_core/models.py  
- engines/typography_core/service.py  
- engines/typography_core/tests/test_i03_typography.py  
- engines/video_text/service.py (only if integrating typography outputs)  
- engines/video_text/tests/test_video_text_service.py (only if service changes)  
- engines/image_core/backend.py (text rendering integration only)  
- engines/image_core/tests/test_i01_composite.py (only if text layer changes)  
- docs/engines/media_program/PHASE_I03_typography_variable_fonts.md  
- docs/engines/FONTS_HELPER.md (registry notes only)  
- docs/engines/video_audio_atomic_design.md (text overlay notes only)  
- READ-ONLY context: other files.  
STOP RULE: If you believe any file outside this list must be changed to complete this phase, stop and return a report instead of editing it.

4. Implementation checklist  
- Design & registry  
  - Expand font registry with variable fonts; parse axis metadata; add default font packs and deterministic lookup order.  
  - Document axis bounds and safe defaults; reject missing fonts/axes out of bounds with clear errors.  
- Rendering (renderer.py, service.py)  
  - Implement shaping/layout with support for line wrapping, alignment, tracking/leading, variable font axis overrides; deterministic DPI/antialias settings.  
  - Provide service API to render text to image (optionally register artifact) and return bbox metrics; include font/version info in meta.  
  - Add caching (optional) for repeated text layouts (hash text+font+axes) to avoid recompute.  
- Integration  
  - Update video_text to use typography_core outputs for titles/lower-thirds; keep backward compatibility.  
  - Update image_core text layer rendering to consume registry/fonts; ensure masks/adjustments still apply.  
- Validation & safety  
  - Clamp sizes/axes; clear errors for missing fonts/axes; deterministic outputs (same input -> same image/metrics).  
- Docs sync  
  - Update registry guide (FONTS_HELPER) and this doc with supported fonts/axes/examples.  
- If additional files appear to need changes, STOP and report; do not refactor outside the modules listed in Modules to touch.

5. Tests  
- engines/typography_core/tests/test_i03_typography.py: axis handling, wrapping/alignment metrics, deterministic sizing, error on missing font/invalid axis.  
- engines/video_text/tests/test_video_text_service.py: uses typography_core outputs, meta integrity, backward compatibility.  
- engines/image_core/tests/test_i01_composite.py (extend) or new: text layer rendering with registry fonts and masks.  
Additional required cases:  
- Determinism: same text/font/axes -> same image hash/metrics.  
- Error path: unknown font/axis out of bounds throws clear error.  
- Optional cache hit/miss if caching added.

6. Docs & examples  
- Update this phase doc with font registry guide, axis support, text properties, and example requests.  
- Update FONTS_HELPER.md/ENGINE_INVENTORY if font packs added.  
- Add example: render “Hello Northstar” with font X, weight axis 700, width 90%, max width 400px → returns image artifact + bbox; show integration in video_text overlay.

7. Guardrails for implementers  
- Do not touch any auth/tenant/RequestContext/strategy lock/firearms/budget/safety code.  
- Do not touch any /ui, /core, or /tunes directories.  
- Do not modify any connectors, orchestration flows, manifests, or Nexus/agent behaviour; this phase is engines-only muscle.  
- Do not add or change any vector store / memory / logging pipelines; only use existing helpers in modules listed above.  
- If you need a new artifact kind or model field, mark CONTRACT CHANGE in this doc and only update explicitly listed files/tests.  
- If additional files appear necessary, STOP and report instead of editing outside the allow-list.  
- Within the allow-list, implement all code/tests/docs to reach the Definition of Done; no TODOs unless a blocking external dependency is documented.

8. Execution note  
Complete this phase (code+tests+docs) strictly within the allow-listed files; if anything outside seems required, stop and report. Within the allow-list, deliver full Definition of Done with passing tests. Then proceed to PHASE_I04 unless a TODO – HUMAN DECISION REQUIRED truly blocks you.
