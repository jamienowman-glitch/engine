# TIMELINE_CRITICAL_TODOS

For feral worker agents implementing **PHASE_T01_pro_timeline_muscle**. Obey the allow-list and STOP RULE in PHASE_T01. Do not touch any code outside engines/video_timeline and listed docs/tests. Dependencies (video_render, video_multicam, video_assist, video_focus_automation) are read-only.

## Checklist (prioritized)

- [x] **T01.1 – Harden timeline models for roles/alignment**  
  Allowed: engines/video_timeline/models.py; tests/test_timeline_models.py  
  Expected: Models expose roles (main/b-roll/music/VO/fx), alignment/meta fields (alignment_offset_ms, scoring_version/cache_key), FX/transition refs, deterministic IDs/ordering; validation for bounds/overlaps. Tests assert defaults, validation errors, and determinism.  
  Tests: `python3 -m pytest engines/video_timeline/tests/test_timeline_models.py`
  *Note: Verified video_role, alignment_applied, and strict transition types with new unit tests.*

- [x] **T01.2 – Clip add/trim/split/move/ripple ops**  
  Allowed: engines/video_timeline/service.py; tests/test_timeline_models.py or test_timeline_integration.py  
  Expected: Service supports add, trim, split, move, ripple move on clips with snapping rules and deterministic ordering; ripple adjusts downstream clips on same track; ripple move shifts neighbor clips. Tests cover each op, snapping, ripple behavior, and determinism.  
  Tests: `python3 -m pytest engines/video_timeline/tests/test_timeline_integration.py`
  *Note: Implemented trim_clip, split_clip, move_clip, and _shift_track_after. Verified ripple behavior.*

- [x] **T01.3 – Transitions & FX hooks to render presets**  
  Allowed: engines/video_timeline/service.py, models.py; tests/test_timeline_integration.py  
  Expected: Timeline stores transition/FX references mapping to existing video_render catalogs (no render logic changes); validation of IDs/params; meta captured for downstream render requests. Tests assert mapping stored, invalid IDs rejected, and render payload includes refs (mocked).  
  Tests: `python3 -m pytest engines/video_timeline/tests/test_timeline_integration.py`
  *Note: Added validation for KNOWN_FILTERS and transition duration. Integration tests pass.*

- [x] **T01.4 – Multicam promotion into sequences**  
  Allowed: engines/video_timeline/service.py; tests/test_timeline_integration.py  
  Expected: Service consumes V04 multicam alignment/auto-cut outputs and builds sequences/tracks/clips with preserved alignment meta (alignment_version/cache_key); deterministic ordering/IDs; rejection on missing tenant/env handled upstream. Tests assert promotion produces expected tracks/clips and preserves meta.  
  Tests: `python3 -m pytest engines/video_timeline/tests/test_timeline_integration.py`
  *Note: Added promote_multicam_to_sequence. Verified sequence/track/clip creation with meta preservation.*

- [x] **T01.5 – Assist/focus to clips/automation**  
  Allowed: engines/video_timeline/service.py; tests/test_timeline_integration.py  
  Expected: Highlight suggestions become tracks/clips with scoring meta; focus suggestions become automation keyframes; deterministic results; warnings when artifacts absent. Tests assert creation, meta presence, and fallback behavior.  
  Tests: `python3 -m pytest engines/video_timeline/tests/test_timeline_integration.py`
  *Note: Added ingest_assist_highlights and apply_focus_automation. Verified creation of clips and keyframes.*

- [x] **T01.6 – Deterministic persistence & reload**  
  Allowed: engines/video_timeline/service.py, models.py; tests/test_timeline_integration.py  
  Expected: Save/reload yields same IDs/order; snapshot/export/import documented; collision-safe ID generation; ordering rules enforced. Tests assert identical structures after round-trip.  
  Tests: `python3 -m pytest engines/video_timeline/tests/test_timeline_integration.py`
  *Note: Verified round-trip persistence, correct track sorting by order, and clip sorting by time.*

- [x] **T01.7 – HTTP API polish & validation**  
  Allowed: engines/video_timeline/routes.py, service.py; tests/test_timeline_routes.py  
  Expected: CRUD/edit endpoints for project/sequence/track/clip/transition/automation and edit ops; validation errors return 4xx with messages; backward compatibility preserved. Tests assert happy/negative paths and status codes.  
  Tests: `python3 -m pytest engines/video_timeline/tests/test_timeline_routes_advanced.py`
  *Note: Implemented routes for trim, split, move, promote, ingest, apply. Verified with advanced route tests using create_app fixture.*

- [x] **T01.8 – Docs/examples**  
  Allowed: docs/engines/video_timeline/*.md, docs/engines/media_program/PHASE_T01_pro_timeline_muscle.md  
  Expected: Add example JSON for full timeline and “YouTube vlog” example with A-roll/B-roll/music, captions ref, focus automation; document snapping/ripple rules and ID determinism; align with DoD.  
  Tests: n/a (docs) but ensure examples match model fields.
  *Note: Created docs/engines/video_timeline/examples.md covering YouTube vlog scenario with Multicam, Assist, and Focus integration examples.*
