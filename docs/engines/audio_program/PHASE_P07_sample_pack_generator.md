# Phase P7 – Sample Pack Generator

Goal: Automatically generate structured sample packs from field recordings using the existing detection, FX, and normalisation pipeline.

Scope
- In: sample_pack_engine (new), orchestration across field_to_samples -> audio_fx_chain -> audio_normalise -> packaging, deterministic naming/grouping, media_v2 registration, docs/tests.
- Out: video, UI, auth/spine/connectors, unrelated engines.

Modules / files to touch
- engines/sample_pack_engine/service.py, models.py
- engines/sample_pack_engine/naming.py for deterministic folder/file naming
- engines/audio_field_to_samples, audio_fx_chain, audio_normalise (invoked, not rewritten)
- engines/audio_sample_library (optionally expose packs)
- media_v2 artifact/meta for pack outputs (zip? folder descriptors)
- Tests under engines/sample_pack_engine/tests
- Docs: docs/engines/audio_program/PHASE_P07_sample_pack_generator.md

Implementation steps
1) IO models: SamplePackRequest {asset_ids[], genres/tags, min_hits, min_loops, fx_preset?, normalise_target_lufs, naming_convention}, SamplePackResult {pack_id, artifacts[], manifest}.
2) Pipeline: run field_to_samples on inputs; apply fx_chain presets and normalization to resulting artifacts; group into folders by type and tag; generate manifest (JSON) listing artifact ids, source assets, processing meta.
3) Naming: deterministic names using seed + source + role (e.g., `pack_{id}/drums/kick_01.wav`); encode bpm/key in filenames when available.
4) Packaging: optional zip artifact registered via media_v2 (`kind=sample_pack`); store manifest as meta or sidecar artifact.
5) Idempotence: reuse processed artifacts if already present; avoid duplicate work across runs with same input/config hash.

Tests
- Happy: given fixture field recordings, pack contains expected counts and naming, manifest references correct artifacts and lineage.
- Edge: insufficient hits/loops triggers clear error; rerun with same inputs produces identical pack; varying presets yields different manifest hash.
- Performance: ensure pipeline handles multiple assets without race conditions; bounded parallelism.

Safety / non-goals
- No tenant/auth changes; no external distribution connectors.
- Do not duplicate existing library logic; reuse engines rather than rewriting detection/FX/normalization.

On completion of Phase P7:
- Immediately proceed to Phase P8 using its phase doc.
- Do not pause for human review unless tests fail or you hit an explicit TODO/STOP marker.
