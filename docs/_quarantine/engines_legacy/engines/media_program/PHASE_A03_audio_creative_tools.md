1. Goal  
Improve creative stack: expand FX/macro catalog, strengthen groove extraction, time/pitch quality, and sampling pipeline scoring to deliver DAW-lite creative tools.

North star + Definition of Done  
- North star slice: Beat-maker/podcast DAW-lite—workers can run field_to_samples to get scored hits/loops/phrases, apply FX/macro presets, resample with quality presets, extract groove profiles, and query a sample library by score/brightness/key/role.  
- Definition of Done:  
  - FX/macro catalogs validated with deterministic ffmpeg graphs; presets clamp knobs/dry_wet and tag artifacts with preset/meta.  
  - Groove extraction robust to silence, supports 8/16/32 subdivisions, deterministic offsets, and is queryable.  
  - Resample supports quality/formant-preserving presets with clamped pitch/tempo; meta records changes.  
  - field_to_samples scores/filter hits/loops/phrases, idempotent cache keys, partial-failure tolerant.  
  - Sample library supports filters (quality score, brightness/key/role) with pagination.  
  - Tests cover success/failure, validation, determinism, and cache behavior.

2. Scope (In / Out)  
- In: audio_fx_chain, audio_macro_engine, audio_groove, audio_resample, audio_field_to_samples, audio_sample_library search.  
- Out: backend dependency checks (A01), UI/auth/tenant/safety, orchestration.

3. Modules to touch  
- engines/audio_fx_chain/service.py  
- engines/audio_fx_chain/presets.py  
- engines/audio_fx_chain/tests/test_fx_chain.py  
- engines/audio_fx_chain/tests/test_a03_creative.py  
- engines/audio_macro_engine/service.py  
- engines/audio_macro_engine/presets.py  
- engines/audio_macro_engine/tests/test_macro.py  
- engines/audio_groove/service.py  
- engines/audio_groove/dsp.py  
- engines/audio_groove/tests/test_groove.py  
- engines/audio_resample/service.py  
- engines/audio_resample/tests/test_resample.py  
- engines/audio_field_to_samples/service.py  
- engines/audio_field_to_samples/tests/test_pipeline.py  
- engines/audio_sample_library/service.py  
- engines/audio_sample_library/tests/test_library.py  
- docs/engines/media_program/PHASE_A03_audio_creative_tools.md  
- docs/engines/ENGINE_INVENTORY.md (only if artifact/meta fields change)  
- READ-ONLY context: other files.  
STOP RULE: If you believe any file outside this list must be changed to complete this phase, stop and return a report instead of editing it.

4. Implementation checklist  
- FX/Macro presets (service.py, presets.py)  
  - Expand FX presets (saturation_sizzle, delay_dream, wide_spread, ambient_tail, transient_snap, tape_warmth) with deterministic ffmpeg graphs; annotate intensity/latency.  
  - Expand Macro presets (sparkle_tap, breathing_cloud, tight_snap) with knob whitelists and sanitization.  
  - Clamp knob ranges/dry_wet; validate preset IDs; raise clear errors on unknown IDs; tag artifacts with preset_id, params_applied, knob_overrides, backend_version.  
- Groove extraction (service.py, dsp.py)  
  - Improve onset detection robustness; support subdivisions 8/16/32; deterministic offset arrays (fill missing with zeros/interpolation); seedable for tests.  
  - Expose get_groove_profile service; store subdivision/avg_offset in artifact meta.  
- Resample (service.py)  
  - Add quality presets (draft/high) and preserve_formants toggle; clamp tempo/pitch deltas; record meta (quality_preset, preserve_formants, resample_params).  
  - Reject empty filter strings with clear warning and fallback (return original) tagged in meta.  
- field_to_samples (service.py)  
  - Compute confidence/quality scores from hits/loops/phrases; filter below threshold; include source offsets and scores in artifact meta.  
  - Add idempotent cache key (asset+params); allow partial success and per-step errors; ensure artifact registration for successful parts.  
- Sample library (service.py)  
  - Add query filters for quality_score range, brightness, key, role; add pagination (limit/offset) with deterministic ordering; ensure repo indexes as needed.  
  - Tag samples with quality_score/role in metadata; return filtered results.  
- Integration glue  
  - Ensure pattern/arrangement engines can consume groove profiles and scored samples (documented expectations); no new code outside allow-list.  
- Validation & safety  
  - Clamp params and reject invalid inputs; clear errors for missing presets or out-of-range knobs; deterministic outputs for same input+params.  
- Docs sync  
  - Update preset catalog tables, groove algorithm notes, resample meta fields, sample library filters in this doc and ENGINE_INVENTORY if meta changes.

5. Tests  
- engines/audio_fx_chain/tests/test_a03_creative.py: new presets exist, params validated, filter strings deterministic; errors on unknown preset/invalid knobs.  
- engines/audio_fx_chain/tests/test_fx_chain.py: meta tagging, dry_wet clamp, subprocess error propagation.  
- engines/audio_macro_engine/tests/test_macro.py: knob validation, meta tagging, error handling.  
- engines/audio_groove/tests/test_groove.py: subdivisions (8/16/32), deterministic offsets, handling of silence/sparse data.  
- engines/audio_resample/tests/test_resample.py: quality presets, pitch/tempo clamps, preserve_formants toggle, meta assertions, fallback when filter empty.  
- engines/audio_field_to_samples/tests/test_pipeline.py: scoring thresholds, meta contents (scores/offsets/cache_key), partial failure handling, idempotent cache.  
- engines/audio_sample_library/tests/test_library.py: query filters (quality, brightness, key, role), pagination ordering.  
Additional required cases:  
- Determinism: same input+params -> same scores/meta.  
- Negative tests: invalid preset ID/knob raises error; quality_score filter respects thresholds.  
- If any CONTRACT CHANGE, update ENGINE_INVENTORY tests accordingly.

6. Docs & examples  
- Update this phase doc with preset catalog tables, groove algorithm notes, resample presets/meta fields, sample library filter examples.  
- Update ENGINE_INVENTORY if artifact/meta fields change.  
- Add example: POST /audio/field-to-samples on field recording → hits/loops/phrases with scores; apply FX preset via audio_fx_chain; query sample library for quality>0.7 and key=Amin.

7. Guardrails for implementers  
- Do not touch any auth/tenant/RequestContext/strategy lock/firearms/budget/safety code.  
- Do not touch any /ui, /core, or /tunes directories.  
- Do not modify any connectors, orchestration flows, manifests, or Nexus/agent behaviour; this phase is engines-only muscle.  
- Do not add or change any vector store / memory / logging pipelines; only use existing helpers in modules listed above.  
- If you need a new artifact kind or model field, mark CONTRACT CHANGE in this doc and only update explicitly listed files/tests.  
- If additional files appear necessary, STOP and report instead of editing outside the allow-list.  
- Within the allow-list, implement all code/tests/docs to reach the Definition of Done; no TODOs unless a blocking external dependency is documented.

8. Execution note  
Complete this phase (code+tests+docs) strictly within the allow-listed files; if anything outside seems required, stop and report. Within the allow-list, deliver full Definition of Done with passing tests. When done, proceed directly to PHASE_A04 unless a TODO – HUMAN DECISION REQUIRED truly blocks you.

9. Runtime notes & contracts

**FX catalog & metadata**
- Preset roster (`FX_PRESETS`) currently exposes: `clean_hit`, `lofi_crunch`, `bright_snare`, `warm_pad`, `vocal_presence`, `bass_glue`, `sub_rumble`, `tape_warmth`, `wide_chorus`, `transient_snap`, `saturation_sizzle`, `delay_dream`, `wide_spread`, and `ambient_tail`. Each preset projects deterministic filter graphs (HPF→LPF→EQ→Comp→Sat→Reverb→Limiter) and clamped knob ranges; misuse raises `ValueError("Unknown preset")`.
- `FX_PRESET_METADATA` documents `intensity`/`latency_ms` for every preset so downstream render planners can budget latency. Artifacts (`audio_sample_fx`) now expose `params_applied`, `knob_overrides`, `dry_wet`, and `preset_metadata` alongside `backend_info`.

**Groove extraction contract**
- `extract_groove_offsets` normalizes requested subdivisions to 8/16/32, backfills missing steps via `_fill_missing_offsets`, and returns deterministic ms offsets (0 when no onsets). Tests cover 8/16/32 subdivisions, silence fallbacks, and non-empty onset handling.
- `AudioGrooveService.extract_groove` writes `audio_groove_profile` artifacts whose meta stores `subdivision`, `bpm`, `avg_offset`, and `source_artifact_id`. `get_groove_profile` can reload the JSON profile for downstream pattern engines.

**Resample telemetry**
- `AudioResampleService.resample_artifact` clamps tempo scale to [0.5, 2.0], pitch to ±12 semitones, and normalizes `quality_preset` (`draft` vs `quality`) before running `rubberband`. Metadata for `audio_resampled` includes `resample_params` (tempo/pitch keys, `quality_preset`), `quality_preset`, `preserve_formants`, and `backend_info`.
- When no tempo/pitch adjustments occur, the service now logs a warning, returns the original artifact, and emits `meta.returned_original=true` plus `meta.reason="no tempo or pitch changes requested"` so callers can opt into reprocessing if needed.

**Field-to-samples scoring & caching**
- `FieldToSamplesService.process_asset` computes `score`/`offset_ms` per hit/loop/phrase, filters by `min_quality_score` (clamped to [0,1]), deduplicates in request order, and stores the scoreboard in `summary_meta.score_details`. Partial failures record per-step error messages (`summary_meta.errors`), `filtered_counts`, and continue with available detections.
- Idempotent cache keys hash `(asset_id,run_flags,min_quality_score,params,jsonified params,backend_versions)`. Every summary now surfaces `summary_meta.backend_versions` plus `summary_meta.cache_key` (SHA-256) so downstream flows can tell whether to reuse results.

**Sample library filters**
- Queries support quality score ranges (`min_quality_score`, `max_quality_score`), brightness (`min_brightness`, `max_brightness`), key root (`key_root`), role, and BPM/bars. Results sort deterministically by `(kind, source_start_ms, artifact_id)` and honor `limit`/`offset` pagination. Descriptors expose `quality_score`, `role`, `brightness`, `key_root`, and raw `meta` for downstream UI filtering.

**Example flow**
1. POST `/audio/field-to-samples` with `{tenant_id, env, asset_id, min_quality_score=0.7}` → returns scored hits/loops/phrases and `summary_meta.cache_key`.
2. Apply an FX preset via `/audio/fx-chain/apply` (e.g., `preset_id="saturation_sizzle"`, `dry_wet=0.8`, `params_override={"sat": {"drive": 0.8}}`) so the resulting `audio_sample_fx` artifact includes `params_applied`, sanitized overrides, and `backend_info`.
3. Query `/audio/sample-library` for `quality_score>=0.7` and `key_root="Amin"`; the service filters candidate artifacts and paginates with deterministic ordering so automations can consistently grab the same sample set for the creative session.
