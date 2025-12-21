# Phase P12 – Harmonic and Scale Adaptation

Goal: Keep loops and patterns musically coherent across key/scale changes by detecting key/scale and adapting pitch while preserving relationships between roles.

Scope
- In: key/scale detection module, adaptation engine for samples/patterns, harmony map definitions, integration with audio_timeline/patterns, docs/tests.
- Out: video, UI, auth/spine/connectors, unrelated engines.

Modules / files to touch
- engines/audio_harmony/service.py, models.py (new)
- engines/audio_harmony/detector.py (key/scale detection)
- engines/audio_harmony/adapter.py (pitch-shift plans for samples/patterns)
- engines/audio_pattern_engine integration (apply harmonic map)
- audio_resample (reuse pitch-shift backend) if needed
- Tests under engines/audio_harmony/tests and integration with pattern/timeline
- Docs: docs/engines/audio_program/PHASE_P12_harmonic_scale_adaptation.md

Implementation steps
1) Detection: implement key/scale estimator per sample/loop using chroma/hpcp (librosa) with deterministic parameters; output KeyEstimate {key, scale, confidence}.
2) Harmony map: define progressions as abstract degree sequences (I–V–vi–IV etc.); store in data/templates.
3) Adaptation: for a target key/scale, compute pitch-shift in semitones per sample/track; apply via audio_resample or inline rubberband backend; ensure formant preservation flag; update artifact meta with original/target key.
4) Pattern integration: apply harmony map to melodic/bass roles, keeping intervals consistent; ensure drums unaffected.
5) Timeline integration: update clip references to adapted artifacts; ensure bar alignment preserved after pitch-shift/stretch.

Tests
- Happy: detect key on known samples; adapt pattern to new key and confirm pitch shifts match expected semitones; harmony map applied consistently across roles.
- Edge: low-confidence detection falls back to default key; non-tonal material returns “unknown”; extreme pitch shifts clamped with warning.
- Determinism: repeated detection/adaptation yields same outputs.

Safety / non-goals
- No tenant/auth changes; no UI.
- Avoid stub detectors; if backend unavailable, mark skip with explicit reason.

On completion of Phase P12:
- Immediately proceed to Phase P13 using its phase doc.
- Do not pause for human review unless tests fail or you hit an explicit TODO/STOP marker.
