# Phase P3 – Audio Timeline Engine

Goal: Place hits/loops/phrases on a tempo grid with track controls and render a stereo mixdown with correct timing and automation.

Scope
- In: audio_timeline engine (projects, sequences, tracks, clips, tempo grid), audio_render engine for mixdown, media_v2 artifact registration, automation for volume/pan, loudnorm option.
- Out: video timelines, UI, auth/spine/connectors, unrelated engines.

Modules / files to touch
- engines/audio_timeline/models.py, service.py, routes.py
- engines/audio_render/service.py, models.py, routes.py
- audio_timeline automation helpers (volume/pan envelopes)
- media_v2 registration for rendered artifacts (kind `audio_render`)
- Tests under engines/audio_timeline/tests, engines/audio_render/tests
- Docs: docs/engines/audio_program/PHASE_P03_audio_timeline_render.md

Implementation steps
1) Define timeline models: Project, Sequence {bpm, time_signature, duration_ms}, Track {order, mute, volume_db, pan, automation}, Clip {artifact_id, in_ms, out_ms, start_ms_on_timeline, gain_db, fade_in/out, loop_mode?}, Automation {param, keyframes}. Keep contracts additive (mark CONTRACT CHANGE if shapes differ from existing types).
2) CRUD/HTTP: add routes for projects/sequences/tracks/clips and automation akin to video_timeline but audio-only; ensure deterministic validation (no overlapping clips on same track unless explicitly allowed).
3) Render planner: translate timeline to ffmpeg/sox mix plan respecting bpm grid; apply per-track gain/pan, fades, automation (interpolate linearly), loudnorm optional at master.
4) Execution: run ffmpeg/sox to mix; register output artifact via media_v2 with meta {bpm, time_signature, render_profile?, automation_applied}. Support dry-run plan for tests.
5) Alignment: ensure clip start_ms_on_timeline aligns to bpm grid (ticks); provide helpers to convert bars/beats to ms for callers.
6) Caching: optional reuse of render if timeline hash and inputs unchanged (only if straightforward; otherwise note TODO).

Tests
- Happy: multi-track mix with hits/loops aligns to expected bar positions; automation applied (gain ramp, pan sweep) matches numeric expectations; loudnorm output within tolerance.
- Edge: overlapping clips flagged or mixed per rule; muted tracks excluded; very short clips at edges; tempo changes (if unsupported, assert clear error).
- Dry-run vs execution: plan matches executed mix in duration and clip ordering.

Safety / non-goals
- No tenant/auth changes; no UI or LLM logic.
- Keep timeline audio-only; do not reuse video models unless compatible.

On completion of Phase P3:
- Immediately proceed to Phase P4 using its phase doc.
- Do not pause for human review unless tests fail or you hit an explicit TODO/STOP marker.
