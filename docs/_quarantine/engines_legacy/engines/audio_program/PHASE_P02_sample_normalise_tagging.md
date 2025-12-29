# Phase P2 – Sample Normalisation and Tagging

Goal: Normalize loudness/peaks for all samples and attach deterministic tags/features (tempo, key estimate, spectral metrics) to make the library browsable and balanced.

Scope
- In: audio_normalise engine, auto-tag feature extractor, sample metadata updates, media_v2 artifact/meta writes, library query exposure.
- Out: video changes, UI, tenant/auth/spine work, unrelated engines.

Modules / files to touch
- engines/audio_normalise/service.py, models.py, dsp_backend.py
- engines/audio_feature_tagging (new) or module under audio_normalise for tagging
- engines/audio_sample_library (extend queries/filters for tags/features)
- media_v2 artifact/meta helpers
- Tests under engines/audio_normalise/tests, engines/audio_sample_library/tests
- Docs: docs/engines/audio_program/PHASE_P02_sample_normalise_tagging.md

Implementation steps
1) IO models: NormaliseRequest {artifact_id or asset_id, target_lufs, peak_ceiling_dbfs, allow_clip_guard, output_format, tenant/env if present}, NormaliseResult {normalized_artifact_id, lufs_measured, peak_dbfs, meta}.
2) DSP: implement LUFS/peak normalization using pyloudnorm/ffmpeg; ensure deterministic measurement (fixed block size, true-peak if supported). Apply limiter to avoid overs.
3) Tagging: compute tempo (librosa.beat), key estimate (librosa or librosa-hz-to-key heuristic), spectral centroid, brightness, noisiness (zero-crossing rate); attach to artifact meta; store tags (e.g., `key=Cmin`, `tempo_bpm=90`).
4) Library integration: expose filters for key, bpm range, brightness/noisiness buckets; ensure existing endpoints remain backward compatible (mark CONTRACT CHANGE if shapes change).
5) Pipelines: optionally hook into field_to_samples to auto-normalize outputs; respect opt-in flag to avoid breaking contracts if not desired (default off unless already normalized).
6) Caching: reuse normalized/tagged artifacts if identical request already processed (cache key based on source artifact id + target params + backend_version).

Tests
- Happy: normalize fixture samples to target LUFS/peak; assert measured loudness within tolerance; tags match expected key/tempo on known loops.
- Edge: silence input (no division by zero), extremely dynamic input, short transient-only samples (tempo detection should fall back gracefully).
- Library: query filters return correctly tagged artifacts and remain deterministic.

Safety / non-goals
- No tenant/auth changes; no external connectors.
- Avoid stub tagging; if feature cannot be computed, return empty with explicit meta flag.

On completion of Phase P2:
- Immediately proceed to Phase P3 using its phase doc.
- Do not pause for human review unless tests fail or you hit an explicit TODO/STOP marker.
