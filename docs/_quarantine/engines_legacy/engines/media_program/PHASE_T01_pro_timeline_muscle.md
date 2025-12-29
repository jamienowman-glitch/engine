# PHASE_T01_pro_timeline_muscle

## 1. Goal  
Bring the timeline engine to a “CapCut/DaVinci-lite” experience for personal YouTube/demo edits: multi-track video/audio with fast, deterministic CRUD and edit ops that leverage the already-stable V01–V04 video stack.

## 2. North star + Definition of Done  
- North star: A pro-feeling timeline that supports multi-track video/audio (A-roll, B-roll, music/VO), clip trim/split/move/ripple edits, snapping, basic transitions/FX via existing render presets, multicam sequence promotion, and turning highlight/focus suggestions into real tracks/clips/automation.  
- Definition of Done (API/client observable):  
  - Create/read/update Project, Sequence, Track, Clip, Transition, Automation/Keyframes with roles (main, b-roll, music, VO, fx).  
  - Add/trim/split/move (and ripple-style) edits on clips with deterministic ordering/IDs; snapping rules documented.  
  - Apply transitions/FX hooks that map to existing video_render presets/catalogs (no new render logic).  
  - Ingest multicam alignment results (from V04) to auto-build sequences/tracks.  
  - Convert assist/focus outputs (from V04) into Clips/Tracks/Automation.  
  - Save/reload timelines deterministically: same inputs → same plan, stable IDs/meta; persistence tested.  
  - HTTP routes stable for CRUD and edit operations; validation returns clear 4xx on bad inputs.  
  - Tests prove models, service ops, routes, and integration with render/multicam/assist (read-only dependencies).

## 3. Scope (In / Out)  
- In: `engines/video_timeline` models/service/routes/tests; docs under docs/engines/media_program and docs/engines/video_timeline (docs-only). Light schema adjustments to integrate V04 outputs (alignment/assist/focus) allowed within allow-list.  
- Out: No changes to detectors, video_render, video_multicam, video_assist, video_focus_automation (read-only dependencies). No auth/tenant/RequestContext changes. No /ui, /core, or /tunes edits. No Nexus/orchestration/agent logic.

## 4. Modules to touch (for future workers)  
- engines/video_timeline/models.py  
- engines/video_timeline/service.py  
- engines/video_timeline/routes.py  
- engines/video_timeline/tests/test_timeline_models.py  
- engines/video_timeline/tests/test_timeline_routes.py  
- engines/video_timeline/tests/test_timeline_integration.py  
- docs/engines/media_program/PHASE_T01_pro_timeline_muscle.md  
- docs/engines/video_timeline/*.md (docs-only, optional design notes)  
- **READ-ONLY CONTEXT:** engines/video_render/, engines/video_multicam/, engines/video_assist/, engines/video_focus_automation/ (do not modify).  
> STOP RULE: If you believe any file outside this list must be changed to complete this phase, stop and return a report instead of editing it.

## 5. Implementation checklist (mechanical)  
- **Model shaping:** Ensure Project/Sequence/Track/Clip/Transition/Automation models include roles, alignment/meta fields (e.g., alignment_offset_ms, scoring_version, cache keys), FX/transition references (ids/params), deterministic IDs, ordering fields, and validation of bounds.  
- **Clip ops:** Implement add/trim/split/move/ripple operations with clear rules for overlaps, snapping thresholds, and ordering; ensure ripple adjusts downstream clips on same track; preserve determinism.  
- **Transitions/FX hooks:** Allow attaching transition/FX references to clips/tracks/sequences that map directly to existing video_render catalogs (no render logic changes); validate IDs/params and store meta for downstream render.  
- **Multicam integration:** Add service entrypoint to consume V04 multicam alignment/auto-cut outputs and promote them into sequences/tracks/clips with preserved meta (alignment_version, cache_key).  
- **Assist/focus integration:** Add service entrypoints to ingest highlight/focus suggestions and materialize them into clips/tracks/automation keyframes with source meta.  
- **Persistence/determinism:** Ensure saves/reloads produce stable IDs/order; sorting rules documented; snapshot/export/import flows tested; collision-safe ID generation.  
- **HTTP API:** CRUD + edit endpoints for timeline entities and edit ops; validation returns 4xx on bad input; backward compatibility maintained where applicable.  
- **Docs:** Add/refresh timeline design note (optional) and examples per section 7 within docs-only paths.  
- Each step must be done strictly within allow-listed modules; if more is needed, STOP and report.

## 6. Tests  
- engines/video_timeline/tests/test_timeline_models.py — model invariants, roles, alignment/meta fields, ID determinism.  
- engines/video_timeline/tests/test_timeline_routes.py — CRUD/edit endpoints, validation errors, 4xx on bad inputs, backward compatibility.  
- engines/video_timeline/tests/test_timeline_integration.py — end-to-end: build timeline (with transitions/FX refs), apply multicam/assist/focus inputs, persist/reload determinism, and ensure render request payloads reference catalog IDs (mock render).  
- Commands:  
  - `python3 -m pytest engines/video_timeline/tests/test_timeline_models.py`  
  - `python3 -m pytest engines/video_timeline/tests/test_timeline_routes.py`  
  - `python3 -m pytest engines/video_timeline/tests/test_timeline_integration.py`

## 7. Docs & examples  
- Provide example JSON for full timeline: project → sequence → tracks (main, b-roll, music) → clips → transitions/FX refs → automation/keyframes.  
- Example “YouTube vlog” timeline: A-roll (face clip), B-roll overlays, music bed, captions artifact ref, focus automation applied to keyframes; show how multicam alignment builds sequence and assist suggestions become clips.  
- Place examples/design notes under docs/engines/video_timeline/*.md (docs-only) if needed.

## 8. Guardrails for implementers  
- Do not touch any auth/tenant/RequestContext/strategy lock/firearms/budget/safety code.  
- Do not touch any /ui, /core, or /tunes directories.  
- Do not modify any connectors, orchestration flows, manifests, or Nexus/agent behaviour; this phase is engines-only muscle.  
- Do not add or change any vector store / memory / logging pipelines; only use existing helpers in the allow-listed files.  
- If you need to change HTTP signatures or models, mark CONTRACT CHANGE in this doc and limit edits to the allow-listed video_timeline files and matching tests.

## 9. Execution note  
Execution note: A worker executing this phase must complete code + tests + docs strictly within the allow-listed files and deliver the full Definition of Done. If any work appears to require changes outside the allow-list, they must STOP and report instead of editing. Once PHASE_T01_pro_timeline_muscle is complete, we will run a fresh architect audit before defining any further timeline phases.
