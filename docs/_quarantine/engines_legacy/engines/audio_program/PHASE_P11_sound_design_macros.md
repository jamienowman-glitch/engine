# Phase P11 – Sound Design Macro Engine

Goal: Define reusable, parametric macro chains for sound design (impacts, whooshes, swells) that produce single artifacts with captured lineage.

Scope
- In: macro definitions (graphs of FX operations), macro execution engine, presets, artifact registration, docs/tests.
- Out: video, UI, auth/spine/connectors, unrelated engines.

Modules / files to touch
- engines/audio_macro_engine/service.py, models.py, presets.py
- engines/audio_macro_engine/compiler.py (graph -> FX chain using audio_fx_chain or inline DSP)
- media_v2 artifact handling for macro outputs (`audio_macro` kind) with meta
- Tests under engines/audio_macro_engine/tests
- Docs: docs/engines/audio_program/PHASE_P11_sound_design_macros.md

Implementation steps
1) Macro schema: MacroDefinition {id, nodes: [{type, params}], edges/order, controls: {macro_knobs}}; presets such as impact_01, whoosh, reverse_swell.
2) Execution: compile macro graph to ordered DSP steps (reuse audio_fx_chain components); allow knob overrides that map to params; ensure deterministic ordering and seeds.
3) IO: MacroRequest {source_artifact_id or synth tone generator options, macro_id, knob_overrides, output_format}; MacroResult {artifact_id, meta {macro_id, knobs_resolved, backend_version}}.
4) Lineage: register outputs via media_v2 with parent link and macro metadata; store intermediate stats (loudness, duration) for auditing.
5) Validation: detect cycles/conflicts in macro graph; reject unsupported node types.

Tests
- Happy: run each preset on fixture sample; assert loudness/spectral changes within expected ranges; reverse_swell reverses tail, whoosh adds rise.
- Edge: missing source artifact (error), knob values out of range (clamp), cycle detection.
- Determinism: same macro + knobs yields identical output stats/hashes.

Safety / non-goals
- No tenant/auth changes; no UI; no LLM logic.
- Do not introduce stubs—implement real DSP or clearly specify backend.

On completion of Phase P11:
- Immediately proceed to Phase P12 using its phase doc.
- Do not pause for human review unless tests fail or you hit an explicit TODO/STOP marker.
