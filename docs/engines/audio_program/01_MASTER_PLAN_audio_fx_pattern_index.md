# Audio FX and Pattern Maker – Phase Index (P0–P15)

Use this as the single entrypoint for the audio music-making program. It builds on existing sample spine work (see 00_MASTER_PLAN_samples.md) and runs phases back-to-back without pauses. Scope is audio-only (samples, FX, patterns, timelines, arrangements, cross-modal mapping). Out of scope: video editor changes, 3D/HAZE, UI, spine/auth/connectors.

- P0 – Field to Samples: real DSP hits/loops/phrases and pipeline hardening (`docs/engines/audio_program/PHASE_P00_field_to_samples.md`).
- P1 – Sample FX Chain: deterministic HPF/LPF/EQ/comp/sat/reverb/limiter presets on samples (`docs/engines/audio_program/PHASE_P01_sample_fx_chain.md`).
- P2 – Sample Normalisation and Tagging: LUFS/peak normalization and deterministic auto-tag features (`docs/engines/audio_program/PHASE_P02_sample_normalise_tagging.md`).
- P3 – Audio Timeline Engine: DAW-lite tracks/clips/automation plus audio_render mixdown (`docs/engines/audio_program/PHASE_P03_audio_timeline_render.md`).
- P4 – Pattern and Groove Engine: template-driven patterns with swing/shuffle onto the grid (`docs/engines/audio_program/PHASE_P04_pattern_groove_engine.md`).
- P5 – Resampling and Song Structure: time-stretch/pitch-shift loops and arrange sections with stem export (`docs/engines/audio_program/PHASE_P05_resampling_song_structure.md`).
- P6 – Multi-Bus Mix Engine: bus routing with per-bus FX and aligned stems/master renders (`docs/engines/audio_program/PHASE_P06_multi_bus_mix.md`).
- P7 – Sample Pack Generator: orchestrate field_to_samples -> FX -> normalize into deterministic packs (`docs/engines/audio_program/PHASE_P07_sample_pack_generator.md`).
- P8 – Groove Extraction and Humanisation: extract groove profiles and apply them without drift (`docs/engines/audio_program/PHASE_P08_groove_extraction_humanisation.md`).
- P9 – Arrangement Suggestion: deterministic skeleton arrangements with section templates (`docs/engines/audio_program/PHASE_P09_arrangement_suggestion.md`).
- P10 – Cross-Modal Link Back to Video: store origin mappings and emit shot lists aligned to audio patterns (`docs/engines/audio_program/PHASE_P10_audio_to_video_origin.md`).
- P11 – Sound Design Macro Engine: macro graphs/presets to generate complex hits/risers (`docs/engines/audio_program/PHASE_P11_sound_design_macros.md`).
- P12 – Harmonic and Scale Adaptation: detect key/scale and adapt patterns/samples to target harmony (`docs/engines/audio_program/PHASE_P12_harmonic_scale_adaptation.md`).
- P13 – Performance Capture and Quantise: import MIDI/onsets and quantise with groove/humanise controls (`docs/engines/audio_program/PHASE_P13_performance_capture_quantise.md`).
- P14 – Source Separation Feed-In: deterministic separation to mine stems then run field_to_samples on outputs (`docs/engines/audio_program/PHASE_P14_source_separation_feed_in.md`).
- P15 – Mix Snapshot and Delta Analyzer: capture mix states and compute diffs/complexity metrics (`docs/engines/audio_program/PHASE_P15_mix_snapshot_delta.md`).
