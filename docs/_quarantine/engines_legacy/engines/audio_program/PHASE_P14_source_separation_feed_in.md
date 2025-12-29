# Phase P14 – Source Separation Feed-In

Goal: Integrate a deterministic source-separation wrapper to mine samples from mixed audio and feed them back into the field-to-samples pipeline with preserved origin metadata.

Scope
- In: separation engine wrapper, integration with field_to_samples, metadata tagging for origins, media_v2 artifact registration for separated stems, docs/tests.
- Out: video, UI, auth/spine/connectors, unrelated engines.

Modules / files to touch
- engines/audio_separation/service.py, models.py (new)
- engines/audio_separation/backend.py (wrap chosen model, e.g., Demucs/MDX; deterministic settings)
- engines/audio_field_to_samples integration hook to run on stems
- media_v2 artifacts for stems (`audio_stem_drum`, `audio_stem_bass`, `audio_stem_vocal`, `audio_stem_other`)
- Tests under engines/audio_separation/tests and field_to_samples integration tests
- Docs: docs/engines/audio_program/PHASE_P14_source_separation_feed_in.md

Implementation steps
1) Backend selection: choose a deterministic separation model/version; expose config in backend.py; document model path and parameters. If GPU optional, ensure CPU path with predictable output (may be slower).
2) IO: SeparationRequest {asset_id or artifact_id, stems=["drums","bass","vocals","other"], output_format, seed?}; SeparationResult {stem_artifacts[], meta {backend_version, quality_metrics}}.
3) Artifact registration: register each stem in media_v2 with kind `audio_stem_*`, meta including source asset/time and model info.
4) Pipeline hook: optional flag in field_to_samples to run separation first, then detectors on each stem; ensure deterministic ordering; mark CONTRACT CHANGE if pipeline request shape changes.
5) Quality checks: measure SDR or energy distribution to detect failure; reject/flag poor separations.

Tests
- Happy: run separation on fixture mix; assert stems sum approximately to original (within tolerance); detectors find expected hits/loops on stems.
- Edge: mono input, short clips, missing requested stem (return empty with warning), model absence (skip with explicit reason).
- Determinism: repeated run yields identical stem stats/metadata.

Safety / non-goals
- No tenant/auth changes; no UI; no external connectors beyond the chosen model download if already present.

On completion of Phase P14:
- Immediately proceed to Phase P15 using its phase doc.
- Do not pause for human review unless tests fail or you hit an explicit TODO/STOP marker.
