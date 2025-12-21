# Phase P4 – Pattern and Groove Engine

Goal: Generate deterministic beat patterns from templates and apply swing/shuffle to place clips on the grid.

Scope
- In: pattern_templates (data), pattern_engine (library + optional HTTP), groove/swing application, integration with audio_timeline clips, fixtures and docs.
- Out: video features, UI, auth/spine/connectors, unrelated engines.

Modules / files to touch
- engines/audio_pattern_engine/service.py, models.py, routes.py
- engines/audio_pattern_engine/templates.py (JSON templates for “boom_bap_90”, “grime_140”, “four_on_the_floor”)
- engines/audio_timeline integration helpers for clip placement
- Tests under engines/audio_pattern_engine/tests and possibly audio_timeline/tests for integration
- Docs: docs/engines/audio_program/PHASE_P04_pattern_groove_engine.md

Implementation steps
1) Define template schema: PatternTemplate {id, bpm_default, time_signature, bars, tracks: [{role, steps per bar, hits list with velocity?}], swing_default}. Store templates as JSON under templates.py or data/.
2) Engine API: PatternRequest {template_id or inline template, sample_set {kick, snare, hat, fx...} artifact_ids, bpm, swing_pct, seed}; output PatternResult {timeline_clips[], applied_swing_ms[], seed_used}.
3) Clip placement: map steps to timeline clips referencing sample artifacts; compute start_ms from bpm grid; set gain/velocity mapping to volume_db; allow repeat bars for requested duration.
4) Groove: implement swing/shuffle by delaying off-beat steps (e.g., 16th swing) with deterministic formula based on swing_pct and seed; ensure bar length preserved.
5) Validation: ensure required sample roles exist; deterministic seeding for sample selection when multiple options available.
6) Optional HTTP: `/audio/patterns/apply`; return timeline snippet ready for insertion into audio_timeline.

Tests
- Happy: apply templates with fixtures; assert clip start_ms positions match expected grid and swing offsets; deterministic outputs given same seed.
- Edge: missing sample roles (error), extreme swing values (clamped), mismatched bpm (template vs request) and adjustment logic.
- Integration: generated clips insert into audio_timeline sequence without overlaps beyond rules.

Safety / non-goals
- No tenant/auth changes; no UI.
- No stochastic randomness without seed; avoid stubbed groove logic.

On completion of Phase P4:
- Immediately proceed to Phase P5 using its phase doc.
- Do not pause for human review unless tests fail or you hit an explicit TODO/STOP marker.
