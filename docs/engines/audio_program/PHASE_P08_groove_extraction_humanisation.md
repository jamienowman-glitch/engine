# Phase P8 – Groove Extraction and Humanisation

Goal: Extract groove timing offsets from real loops and apply them to patterns without drift, enabling humanised but deterministic playback.

Scope
- In: groove_extract and groove_apply helpers/engines, integration with audio_pattern_engine and audio_timeline, deterministic offset computation, docs/tests.
- Out: video, UI, auth/spine/connectors, unrelated engines.

Modules / files to touch
- engines/audio_groove/service.py, models.py (new)
- engines/audio_groove/dsp.py for onset/beat analysis
- engines/audio_pattern_engine (hook for applying groove to generated clips)
- engines/audio_timeline helpers for applying per-clip timing offsets
- Tests under engines/audio_groove/tests and integration with pattern/timeline tests
- Docs: docs/engines/audio_program/PHASE_P08_groove_extraction_humanisation.md

Implementation steps
1) Groove extract: given a drum loop artifact, detect beat grid (librosa.beat or onset strength), compute offsets vs ideal grid at detected bpm; output GrooveProfile {bpm, subdivision, offsets_ms per step, confidence}.
2) Groove apply: apply profile to pattern clips by adjusting start_ms within bar while preserving bar length; allow scaling factor to lighten/deepen groove; ensure deterministic application with seed.
3) Data model: store groove profiles as artifacts (`audio_groove_profile`) in media_v2 with meta {source_artifact_id, bpm, subdivision, offsets, backend_version}.
4) Integration: pattern_engine accepts groove_profile_id or inline; timeline helper applies offsets when placing clips.
5) Bounds: clamp offsets to prevent negative times or bar overflow; ensure no cumulative drift across bars.

Tests
- Happy: extract groove from synthetic swung loop; offsets match known values; applying groove to a straight pattern yields expected shifted positions.
- Edge: noisy or sparse loops (fallback to zero groove with warning), mismatched subdivision requests; ensure multiple bars stay aligned.
- Determinism: repeated extract/apply yields identical offsets and clip positions.

Safety / non-goals
- No tenant/auth changes; no UI.
- Do not introduce random jitter without seed; avoid stub groove logic.

On completion of Phase P8:
- Immediately proceed to Phase P9 using its phase doc.
- Do not pause for human review unless tests fail or you hit an explicit TODO/STOP marker.
