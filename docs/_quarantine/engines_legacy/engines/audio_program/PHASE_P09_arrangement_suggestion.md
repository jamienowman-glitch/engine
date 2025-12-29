# Phase P9 – Arrangement Suggestion (Deterministic Skeleton)

Goal: Build deterministic skeleton arrangements from pattern sets and templates, placing sections on whole bars.

Scope
- In: arrangement_engine, templates for section layouts, integration with audio_timeline (sections, muting per role), deterministic selection based on seed, docs/tests.
- Out: video, UI, auth/spine/connectors, unrelated engines.

Modules / files to touch
- engines/audio_arrangement_engine/service.py, models.py, templates.py
- engines/audio_timeline (section markers, mute/unmute helpers)
- engines/audio_pattern_engine (interface for supplying patterns by role)
- Tests under engines/audio_arrangement_engine/tests and audio_timeline/tests
- Docs: docs/engines/audio_program/PHASE_P09_arrangement_suggestion.md

Implementation steps
1) Templates: define arrangement templates (intro/verse/chorus/bridge/outro) with bar lengths and active roles per section; store JSON in templates.py.
2) API: ArrangementRequest {patterns_by_role with clip lists, template_id, duration_goal_bars?, seed}; output ArrangementResult {sections[], timeline_clips[], section_markers}.
3) Placement: for each section, place clips on the grid starting at section start bar; enforce whole-bar boundaries; allow deterministic randomization of variations if provided (seeded).
4) Muting: apply track mute/unmute per section; ensure automation aligns with section boundaries.
5) Validation: error clearly when required roles are missing; enforce that patterns start/end on bars.

Tests
- Happy: apply template with drums/bass/melody patterns; verify section boundaries, clip counts, and mutes match template; deterministic outputs with same seed.
- Edge: duration shorter/longer than template (truncate or repeat with clear rules), missing roles, odd time signatures if unsupported (explicit error).
- Integration: timeline render matches expected duration and section markers.

Safety / non-goals
- No tenant/auth changes; no UI or LLM logic.
- Keep templates deterministic and data-driven; no orchestration outside engine.

On completion of Phase P9:
- Immediately proceed to Phase P10 using its phase doc.
- Do not pause for human review unless tests fail or you hit an explicit TODO/STOP marker.
