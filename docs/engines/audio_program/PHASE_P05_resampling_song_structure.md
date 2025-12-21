# Phase P5 – Resampling and Song Structure

Goal: Time-stretch and pitch-shift loops to target grids and arrange patterns into full song sections with optional stem export.

Scope
- In: time-stretch/pitch-shift engine, structure/arrangement engine, timeline integration, stem export hooks, media_v2 artifact writes.
- Out: video, UI, auth/spine/connectors, unrelated engines.

Modules / files to touch
- engines/audio_resample/service.py, models.py (new or extend)
- engines/audio_structure_engine/service.py, models.py
- engines/audio_timeline (section/marker support), audio_render (stem export options)
- media_v2 artifact handling for resampled loops and stems (kinds like `audio_resampled`, `audio_stem`)
- Tests under engines/audio_resample/tests, engines/audio_structure_engine/tests, audio_render/tests for stems
- Docs: docs/engines/audio_program/PHASE_P05_resampling_song_structure.md

Implementation steps
1) Resample IO: ResampleRequest {artifact_id, target_bpm, target_semitones?, preserve_formants?, stretch_mode}, ResampleResult {artifact_id, bpm_out, pitch_shift, quality_metrics}. Backend can use rubberband or ffmpeg atempo+asetrate with quality guard; ensure deterministic settings.
2) Structure model: ArrangementTemplate {id, sections with name + bars + active tracks/pattern roles}; ArrangementRequest {patterns_by_role, template_id, bpm, seed}; output timeline clips with mute/unmute per section.
3) Timeline hooks: add section markers to audio_timeline; mute/unmute tracks per section; ensure section boundaries align to bars.
4) Stem export: in audio_render add option to export per-track or per-bus stems (aligned start/end, same sample rate/bit depth); register stems as artifacts.
5) Quality bounds: measure resampling artifacts (SNR or spectral deviation) on fixtures; clamp stretch ratios; add metadata `backend_version` and `quality_score`.

Tests
- Happy: resample loop to new bpm/key; assert duration matches grid and pitch-shift within tolerance; structure engine builds intro/verse/chorus layout deterministically.
- Edge: extreme stretch ratios (reject or clamp), short loops that do not fill bars, missing pattern roles in template (error).
- Stems: verify stems align sample-accurate with master render and have expected channel counts.

Safety / non-goals
- No tenant/auth changes; no UI or connectors.
- Avoid stub resamplers—pick a deterministic backend and document parameters.

On completion of Phase P5:
- Immediately proceed to Phase P6 using its phase doc.
- Do not pause for human review unless tests fail or you hit an explicit TODO/STOP marker.
