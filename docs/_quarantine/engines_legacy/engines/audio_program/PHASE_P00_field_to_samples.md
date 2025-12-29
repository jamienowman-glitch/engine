# Phase P0 – Field to Samples

Goal: Turn raw field recordings into production-grade hits, loops, and voice phrases with real DSP backends and lineage captured in media_v2.

Scope
- In: engines/audio_hits, engines/audio_loops, engines/audio_voice_phrases, engines/audio_field_to_samples pipeline, engines/audio_sample_library queries, media_v2 artifact registration, deterministic DSP config, fixtures/docs under docs/engines/audio_program/.
- Out: video_* engines, UI/frontends, tenant/auth/spine wiring, connectors, orchestration beyond these engines, any new contract changes unless explicitly marked.

Modules / files to touch
- engines/audio_hits/service.py, models.py, backends/*
- engines/audio_loops/service.py, models.py, backends/*
- engines/audio_voice_phrases/service.py, models.py, backends/*
- engines/audio_field_to_samples/pipeline.py (or service.py), models.py
- engines/audio_sample_library/service.py, queries.py
- Tests under engines/audio_hits/tests, engines/audio_loops/tests, engines/audio_voice_phrases/tests, engines/audio_field_to_samples/tests, engines/audio_sample_library/tests
- docs/engines/audio_program/* (append notes only)

Implementation steps
1) Validate DSP backends: ensure hits/loops/phrases use real libs (librosa/ffmpeg); remove stub fallbacks or gate them behind explicit flags. Fix parameters for determinism (seeded randomness, fixed hop lengths).
2) Normalize IO shapes: confirm DerivedArtifact kinds (`audio_hit`, `audio_loop`, `audio_phrase`) and meta fields (bpm, loop_bars, transcript, peak_db, confidence) are consistent across engines; document in models.
3) Strengthen field_to_samples pipeline: enforce preprocessing step (loudnorm/mono) before detectors; parallelize safely with bounded workers; propagate failures with per-detector status; always register artifacts via media_v2 with start_ms/end_ms.
4) Sample library hardening: ensure queries filter on artifact kind/bpm/bars/transcript; add pagination/sorting; cache by tenant/env only if already supported (no new tenant plumbing).
5) Fixtures: curate small audio samples (hits/loops/phrases) under tests/fixtures or sample_media with golden expectations (counts, bpm ranges, phrase segments).
6) Docs: add brief README note referencing this phase and listing supported artifacts and meta fields.

Tests
- Happy paths: detector outputs on fixture files (expected count, bpm tolerance, onset timing within epsilon).
- Edge: quiet files, heavy noise, no onsets, extreme tempo; ensure zero results handled gracefully.
- Pipeline: field_to_samples end-to-end registers artifacts and returns summary counts; failure in one detector does not block others.
- Library: query filters and pagination deterministic; returns correct artifact ids/meta from seeded fixtures.

Safety / non-goals
- No tenant/auth/spine changes; no new orchestration layers.
- No UI; no connectors.
- Avoid stub placeholders—use real DSP or skip with explicit skip + reason in tests.

On completion of Phase P0:
- Immediately proceed to Phase P1 using its phase doc.
- Do not pause for human review unless tests fail or you hit an explicit TODO/STOP marker.
