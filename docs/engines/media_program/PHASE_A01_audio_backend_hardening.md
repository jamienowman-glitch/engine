1. Goal  
Make audio DSP backends reliable: ffmpeg/librosa/demucs availability, error handling, and large-file robustness across detection/FX pipelines to underpin DAW-lite flows.

North star + Definition of Done  
- North star slice: Ableton/Bandlab-lite backbone reliability—hits/loops/phrases/FX/macro/normalise/resample/separation run deterministically on field recordings and podcasts without manual retries.  
- Definition of Done:  
  - Centralized health checks for ffmpeg/ffprobe/librosa/demucs with clear errors; services fail fast when deps missing.  
  - All DSP services validate inputs, clamp params, handle large files safely, and tag artifacts with backend/version/meta.  
  - Separation uses demucs with timeout/model meta and stub fallback; FX/macro presets validated; field_to_samples resilient to partial failures.  
  - Tests cover success/failure paths, missing deps, size guards, deterministic stub outputs, and cross-tenant/context validation where applicable.

2. Scope (In / Out)  
- In: audio_hits/loops/phrases, fx_chain, macro_engine, normalise, resample, separation, field_to_samples plumbing, shared helpers.  
- Out: semantic/ASR upgrades (next phase), UI/auth/tenant, orchestration.

3. Modules to touch  
- engines/audio_hits/service.py  
- engines/audio_hits/tests/test_hits.py  
- engines/audio_hits/tests/test_hits_real.py  
- engines/audio_loops/service.py  
- engines/audio_loops/tests/test_loops.py  
- engines/audio_loops/tests/test_loops_real.py  
- engines/audio_voice_phrases/service.py  
- engines/audio_voice_phrases/tests/test_phrases.py  
- engines/audio_voice_phrases/tests/test_phrases_real.py  
- engines/audio_fx_chain/service.py  
- engines/audio_fx_chain/presets.py  
- engines/audio_fx_chain/tests/test_fx_chain.py  
- engines/audio_macro_engine/service.py  
- engines/audio_macro_engine/presets.py  
- engines/audio_macro_engine/tests/test_macro.py  
- engines/audio_normalise/service.py  
- engines/audio_normalise/tests/test_normalise.py  
- engines/audio_resample/service.py  
- engines/audio_resample/tests/test_resample.py  
- engines/audio_separation/service.py  
- engines/audio_separation/backend.py  
- engines/audio_separation/tests/test_separation.py  
- engines/audio_field_to_samples/service.py  
- engines/audio_field_to_samples/tests/test_pipeline.py  
- engines/audio_shared/health.py (or equivalent health utility)  
- engines/audio_shared/tests (new)  
- docs/engines/media_program/PHASE_A01_audio_backend_hardening.md  
- docs/engines/ENGINE_INVENTORY.md (only if artifact kinds/meta change)  
- READ-ONLY context: all other files.  
STOP RULE: If you believe any file outside this list must be changed to complete this phase, stop and return a report instead of editing it.

4. Implementation checklist  
- Design & health checks  
  - Add centralized probe functions in audio_shared/health.py for ffmpeg/ffprobe/demucs (subprocess with 3s timeout) and librosa (import check); return structured status/version.  
  - Add helper to propagate backend_version and health status into service responses/artifact meta.  
- Input validation & safety (apply in each service listed)  
  - Enforce max input size (e.g., 200 MB) with clear errors; stream downloads to temp with cleanup; retry downloads (bounded).  
  - Clamp params: tempo/pitch ranges (resample), gain/dry_wet/knobs (fx/macro), segment length bounds (hits/loops/phrases), min_quality_score (field_to_samples).  
  - Standardize _ensure_local to support local/GCS/S3 with retries; ensure temp cleanup on success/failure.  
  - Reject missing tenant/env if present; reject `t_unknown`; surface structured errors (no silent fallbacks).  
- Hits/Loops/Phrases (service.py)  
  - Use health checks to select real vs stub backend; stub path deterministic with meta.backend_type="stub".  
  - Tag artifacts with detection scores/confidence and backend_version; enforce min/max segment duration.  
- FX/Macro (service.py + presets.py)  
  - Validate preset IDs/knobs; clamp dry_wet; catch subprocess errors; tag artifacts with preset_id, dry_wet, knob values, backend_version.  
  - Add fallback for missing ffmpeg to raise actionable error; no silent success.  
- Normalise (service.py)  
  - Validate inputs; robustly parse loudnorm output; tag artifact meta with norm_stats/target_lufs/backend_version; enforce size/time guards.  
- Resample (service.py)  
  - Add quality presets (draft/high); clamp tempo/pitch deltas; include meta about changes; fallback path when filter string empty.  
- Separation (service.py + backend.py)  
  - Wire demucs call with model selection and 300s timeout; normalize stem naming; tag artifacts with model/version/runtime/backend_type; stub fallback when demucs missing.  
- Field_to_samples (service.py)  
  - Add idempotent cache key (asset + params); allow partial success with per-step errors; filter by min_quality_score; ensure artifacts registered with meta including source offsets and scores.  
- Logging/metrics  
  - Add structured logging for failures (missing deps, timeouts, invalid params) without PII; include backend_version and cache keys.  
- Backward compatibility  
  - Keep public schemas stable; mark CONTRACT CHANGE in this doc if artifact kinds/meta change and update only the listed files/tests.  
- Docs  
  - Document dependency matrix, limits, and error shapes in this doc; note any artifact/meta changes in ENGINE_INVENTORY.  

5. Tests  
- engines/audio_shared/tests: probe present/missing deps (mocked), timeouts, structured status output.  
- engines/audio_hits/tests/test_hits.py & test_hits_real.py: param clamps, stub fallback when librosa missing, meta tags, size guard.  
- engines/audio_loops/tests/test_loops.py & test_loops_real.py: same as hits with loop params.  
- engines/audio_voice_phrases/tests/test_phrases.py & test_phrases_real.py: missing deps fallback, min/max duration clamps.  
- engines/audio_fx_chain/tests/test_fx_chain.py: preset validation, subprocess error propagation, artifact meta, missing ffmpeg error.  
- engines/audio_macro_engine/tests/test_macro.py: knob validation, error handling, meta tagging.  
- engines/audio_normalise/tests/test_normalise.py: malformed loudnorm handling, size guard, meta contents.  
- engines/audio_resample/tests/test_resample.py: quality presets, pitch/tempo clamps, fallback when filter empty.  
- engines/audio_separation/tests/test_separation.py: demucs timeout/error, stem naming/meta, stub fallback, size guard.  
- engines/audio_field_to_samples/tests/test_pipeline.py: partial failure handling, cache key idempotency, quality filtering, meta assertions.  
Additional required cases:  
- Negative tests for oversized input rejection with clear error.  
- Determinism tests: same input + params -> same artifact meta (backend_version, cache_key).  
- Skip markers for heavy deps; ensure skips noted in test output.

6. Docs & examples  
- Update this phase doc with dependency matrix, timeouts, size limits, error shapes, and cache key guidance.  
- Update ENGINE_INVENTORY if artifact/meta shapes change.  
- Add troubleshooting notes in audio_program overview (missing deps, size guards).  
- Provide example: field recording → hits/loops detection (real backend) → fx preset applied → artifacts registered with meta (backend_version, preset_id).

7. Guardrails for implementers  
- Do not touch any auth/tenant/RequestContext/strategy lock/firearms/budget/safety code.  
- Do not touch any /ui, /core, or /tunes directories.  
- Do not modify any connectors, orchestration flows, manifests, or Nexus/agent behaviour; this phase is engines-only muscle.  
- Do not add or change any vector store / memory / logging pipelines; only use existing helpers in modules listed above.  
- If you need a new artifact kind or model field, mark CONTRACT CHANGE in this doc and only update explicitly listed files/tests.  
- If additional files appear necessary, STOP and report instead of editing outside the allow-list.  
- Within the allow-list, implement all code/tests/docs to reach the Definition of Done; no TODOs unless a blocking external dependency is documented.

8. Execution note  
Complete this phase (code+tests+docs) strictly within the allow-listed files; if anything outside seems required, stop and report. Within the allow-list, deliver full Definition of Done with passing tests. When done, proceed directly to PHASE_A02 unless a TODO – HUMAN DECISION REQUIRED truly blocks you.

9. Dependency matrix  
- `ffmpeg` / `ffprobe` (v6.0+ preferred): required for resample, normalize, FX/macro transcoding, and separation staging; health probes shell `ffmpeg -version` and `ffprobe -version` with a 3 s timeout to assert availability.  
- `librosa` (>=0.10): used by hits/loops/phrases detection pipelines; health check ensures `import librosa` succeeds and surfaces `librosa.__version__`.  
- `demucs` (v4.1): invoked via `python -m demucs`, the probe verifies the CLI, enforces a 300 s timeout per job, and surfaces `demucs.__version__` when available.  
- Stubs: Across services, when a dependency is absent the deterministic fallback path must run with `meta.backend_type="stub"` so downstream consumers can detect the difference while still receiving well-structured metadata.

10. Limits, timeouts, and retries  
- Maximum input payload: 200 MB (209,715,200 bytes). All downloads stream through a temporary file that is cleaned up in success and failure paths, and each download is retried at most twice before emitting `errors.input_too_large` or `errors.transient_download`.  
- Segment duration guardrails for hits/loops/phrases: 0.5 s ≤ duration ≤ 30 s; violations raise a structured validation error with the offending field.  
- Subprocess timeouts: health probes (3 s), general DSP calls (following library defaults), demucs jobs (300 s), and `ffmpeg` operations bubble meaningful timeout errors instead of silently failing.

11. Error shapes and logging  
- Validation error example: `{ "code": "validation_error", "service": "audio_hits", "details": { "field": "duration_sec", "reason": "exceeds maximum allowed" }, "backend_version": "librosa-0.10.0" }`.  
- Missing dependency: `{ "code": "missing_dependency", "service": "audio_fx_chain", "dependency": "ffmpeg", "required_version": "6.0", "backend_version": null }`.  
- Input size errors: `{ "code": "input_too_large", "service": "<name>", "max_bytes": 209715200, "received_bytes": 210000000 }`.  
- Structured logging must always include `backend_version` and cache keys for failures (timeouts, invalid params, missing deps) while avoiding tenant-specific identifiers; logs should also mention retry counts when downloads fail.

12. Cache key guidance  
- Field-to-samples cache keys combine the asset ID, parameter map (`min_quality_score`, `start_offset`, `end_offset`, etc.), and the backend version string, then hash with SHA-256 to drive deterministic artifact reuse.  
- Cache hits must re-emit the original artifact metadata (scores, offsets, `backend_version`) so downstream deduplication stays stable; avoid adding timestamps or non-deterministic fields to cached meta.  
- When a partial failure occurs, return the same cache key alongside per-step error diagnostics so callers can decide whether to retry the whole pipeline.

13. Example pipeline (for docs/troubleshooting)  
- Field recording → hits/loops detection using the real backend (librosa health verified).  
- Resulting segments feed into an FX preset run with validated `preset_id`, clamped `dry_wet`, and knob ranges; artifact meta now includes `backend_version`, `preset_id`, `knob_values`, and detection `confidence_scores`.  
- All artifacts expose `meta.backend_type`, `meta.backend_version`, and cache keys so the entire flow can be replayed deterministically for playback or downstream automation.
