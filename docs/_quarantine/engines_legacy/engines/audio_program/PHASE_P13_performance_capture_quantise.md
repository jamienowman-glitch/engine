# Phase P13 – Performance Capture and Quantise

Goal: Import live performance timing (MIDI or audio onset) and map it onto the grid with optional groove-aware quantisation and humanise controls.

Scope
- In: performance capture (MIDI/import), onset extraction from audio, quantisation engine with groove/humanise options, pattern/timeline integration, docs/tests.
- Out: video, UI, auth/spine/connectors, unrelated engines.

Modules / files to touch
- engines/audio_performance_capture/service.py, models.py (new)
- engines/audio_performance_capture/midi_io.py, onset_detection.py
- engines/audio_quantise/service.py (could be part of same module)
- engines/audio_pattern_engine and audio_timeline integration helpers
- Tests under engines/audio_performance_capture/tests and audio_quantise/tests
- Docs: docs/engines/audio_program/PHASE_P13_performance_capture_quantise.md

Implementation steps
1) Capture IO: accept MIDI files or onset timing lists extracted from audio; PerformanceCaptureRequest {source_midi_path? or audio_artifact_id?, target_bpm, groove_profile_id?, quantise_grid (1/4,1/8,1/16), humanise_amount, seed}.
2) Onset extraction: for audio input, detect onsets (librosa.onset_detect) and map to ms; derive velocity from amplitude.
3) Quantise: snap events to grid considering groove_profile if provided; humanise slider blends between snapped and original timing; deterministic with seed.
4) Output: Pattern or timeline clip placements referencing sample artifacts (for drums) or MIDI-like note events for melodic tracks; attach meta {quantise_grid, groove_profile_id, humanise_amount}.
5) Validation: ensure events stay within bar boundaries; handle overlapping notes gracefully.

Tests
- Happy: quantise synthetic off-grid MIDI to 1/16 grid; apply groove shifts and verify offsets; humanise 0 vs 1 extremes.
- Edge: dense passages (double hits), missing velocity (default), tempo mismatches; ensure no drift across bars.
- Determinism: same seed/input yields identical output.

Safety / non-goals
- No tenant/auth changes; no UI; no DAW connectors.

On completion of Phase P13:
- Immediately proceed to Phase P14 using its phase doc.
- Do not pause for human review unless tests fail or you hit an explicit TODO/STOP marker.
