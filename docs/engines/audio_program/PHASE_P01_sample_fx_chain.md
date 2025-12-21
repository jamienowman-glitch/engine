# Phase P1 – Sample FX Chain

Goal: Provide a deterministic FX chain to make samples sound consistent (HPF/LPF, EQ, compressor, saturation, optional reverb/delay, limiter) with presets and artifact lineage.

Scope
- In: audio_fx_chain engine (new or extend), preset definitions, integration with media_v2 artifacts, sample library linkage, docs/tests under audio_program.
- Out: video stack, UI, tenant/auth/spine work, orchestration outside the FX engine, any unrelated audio engines.

Modules / files to touch
- engines/audio_fx_chain/service.py, models.py, presets.py, dsp/ (backend wrappers)
- engines/audio_fx_chain/routes.py (if HTTP surface is expected)
- engines/audio_sample_library (to surface processed variants if needed)
- media_v2 artifact registration helpers
- Tests under engines/audio_fx_chain/tests
- Docs: docs/engines/audio_program/PHASE_P01_sample_fx_chain.md (this doc), add cross-reference from master index

Implementation steps
1) Define IO models: FxChainRequest {asset_id or artifact_id, preset_id or param_set, output_format?, dry_wet, sample_rate, tenant/env if already in models}, FxChainResult {artifact_id, uri, fx_preset_id, params_applied, loudness_meta}.
2) Build deterministic DSP chain: map preset ids (“clean_hit”, “lofi_crunch”, “bright_snare”, “warm_pad”) to fixed parameter sets; implement chain in a backend module using ffmpeg/sox or python dsp libs (e.g., pyloudnorm + scipy). Ensure order: HPF -> LPF -> EQ -> compressor -> saturation -> optional reverb/delay -> limiter.
3) Artifact handling: read source sample artifact; write processed artifact via media_v2 with kind `audio_sample_fx`; store meta {fx_preset_id, params, backend_version, loudness_pre/post, peak_db}.
4) Routing: provide library function and optional HTTP route `/audio/fx-chain/apply`; enforce deterministic seeds for any random modulation.
5) Logging/plan meta: capture chain steps in result for reproducibility (no orchestration changes).

Tests
- Happy: apply each preset to fixture samples; assert loudness and spectral centroid shift in bounded ranges; ensure limiter prevents clipping.
- Edge: silence input, very loud input, long tail for reverb; ensure runtime bounds and deterministic outputs.
- Regression: preset parameter snapshots; hash or numeric stats to detect drift.

Safety / non-goals
- No tenant/auth changes; no new storage backends beyond media_v2 usage.
- No UI or agent prompts; no LLM involvement.

On completion of Phase P1:
- Immediately proceed to Phase P2 using its phase doc.
- Do not pause for human review unless tests fail or you hit an explicit TODO/STOP marker.
