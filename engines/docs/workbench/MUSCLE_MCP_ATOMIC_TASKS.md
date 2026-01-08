# Atomic Muscle MCP Tasks

Use this list to track progress. Mark tasks as completed when code is merged.
Each muscle requires: `spec.yaml`, `impl.py` (with standard template), registration, and tests.

## VIDEO Lane
### origin_snippets ⚠️ (Missing in Tree)
- **Wrapper Path**: `engines/muscles/origin_snippets/mcp/impl.py`
- [ ] Create `engines/muscles/origin_snippets/mcp/spec.yaml`
- [ ] Create `engines/muscles/origin_snippets/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `origin.snippets.read` (READ, No-GC)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_origin_snippets.py`)

### video_360 ✅
- **Wrapper Path**: `engines/muscles/video_360/mcp/impl.py`
- [ ] Create `engines/muscles/video_360/mcp/spec.yaml`
- [ ] Create `engines/muscles/video_360/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `video.360.read` (READ, No-GC)
  - [ ] `video.360.write` (WRITE, GateChain)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_video_360.py`)

### video_anonymise ✅
- **Wrapper Path**: `engines/muscles/video_anonymise/mcp/impl.py`
- [ ] Create `engines/muscles/video_anonymise/mcp/spec.yaml`
- [ ] Create `engines/muscles/video_anonymise/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `video.anonymise.read` (READ, No-GC)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_video_anonymise.py`)

### video_assist ✅
- **Wrapper Path**: `engines/muscles/video_assist/mcp/impl.py`
- [ ] Create `engines/muscles/video_assist/mcp/spec.yaml`
- [ ] Create `engines/muscles/video_assist/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `video.assist.read` (READ, No-GC)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_video_assist.py`)

### video_batch_render ✅
- **Wrapper Path**: `engines/muscles/video_batch_render/mcp/impl.py`
- [ ] Create `engines/muscles/video_batch_render/mcp/spec.yaml`
- [ ] Create `engines/muscles/video_batch_render/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `video.batch.render.read` (READ, No-GC)
  - [ ] `video.batch.render.submit` (SUBMIT, GateChain)
  - [ ] `video.batch.render.status` (STATUS, No-GC)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_video_batch_render.py`)

### video_captions ✅
- **Wrapper Path**: `engines/muscles/video_captions/mcp/impl.py`
- [ ] Create `engines/muscles/video_captions/mcp/spec.yaml`
- [ ] Create `engines/muscles/video_captions/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `video.captions.read` (READ, No-GC)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_video_captions.py`)

### video_edit_templates ✅
- **Wrapper Path**: `engines/muscles/video_edit_templates/mcp/impl.py`
- [ ] Create `engines/muscles/video_edit_templates/mcp/spec.yaml`
- [ ] Create `engines/muscles/video_edit_templates/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `video.edit.templates.read` (READ, No-GC)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_video_edit_templates.py`)

### video_focus_automation ✅
- **Wrapper Path**: `engines/muscles/video_focus_automation/mcp/impl.py`
- [ ] Create `engines/muscles/video_focus_automation/mcp/spec.yaml`
- [ ] Create `engines/muscles/video_focus_automation/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `video.focus.automation.read` (READ, No-GC)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_video_focus_automation.py`)

### video_frame_grab ⚠️ (Missing in Tree)
- **Wrapper Path**: `engines/muscles/video_frame_grab/mcp/impl.py`
- [ ] Create `engines/muscles/video_frame_grab/mcp/spec.yaml`
- [ ] Create `engines/muscles/video_frame_grab/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `video.frame.grab.read` (READ, No-GC)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_video_frame_grab.py`)

### video_history ✅
- **Wrapper Path**: `engines/muscles/video_history/mcp/impl.py`
- [ ] Create `engines/muscles/video_history/mcp/spec.yaml`
- [ ] Create `engines/muscles/video_history/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `video.history.read` (READ, No-GC)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_video_history.py`)

### video_mask ✅
- **Wrapper Path**: `engines/muscles/video_mask/mcp/impl.py`
- [ ] Create `engines/muscles/video_mask/mcp/spec.yaml`
- [ ] Create `engines/muscles/video_mask/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `video.mask.read` (READ, No-GC)
  - [ ] `video.mask.write` (WRITE, GateChain)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_video_mask.py`)

### video_motifs ✅
- **Wrapper Path**: `engines/muscles/video_motifs/mcp/impl.py`
- [ ] Create `engines/muscles/video_motifs/mcp/spec.yaml`
- [ ] Create `engines/muscles/video_motifs/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `video.motifs.read` (READ, No-GC)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_video_motifs.py`)

### video_multicam ✅
- **Wrapper Path**: `engines/muscles/video_multicam/mcp/impl.py`
- [ ] Create `engines/muscles/video_multicam/mcp/spec.yaml`
- [ ] Create `engines/muscles/video_multicam/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `video.multicam.read` (READ, No-GC)
  - [ ] `video.multicam.write` (WRITE, GateChain)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_video_multicam.py`)

### video_presets ✅
- **Wrapper Path**: `engines/muscles/video_presets/mcp/impl.py`
- [ ] Create `engines/muscles/video_presets/mcp/spec.yaml`
- [ ] Create `engines/muscles/video_presets/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `video.presets.read` (READ, No-GC)
  - [ ] `video.presets.write` (WRITE, GateChain)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_video_presets.py`)

### video_preview ✅
- **Wrapper Path**: `engines/muscles/video_preview/mcp/impl.py`
- [ ] Create `engines/muscles/video_preview/mcp/spec.yaml`
- [ ] Create `engines/muscles/video_preview/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `video.preview.read` (READ, No-GC)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_video_preview.py`)

### video_regions ✅
- **Wrapper Path**: `engines/muscles/video_regions/mcp/impl.py`
- [ ] Create `engines/muscles/video_regions/mcp/spec.yaml`
- [ ] Create `engines/muscles/video_regions/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `video.regions.read` (READ, No-GC)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_video_regions.py`)

### video_render ✅
- **Wrapper Path**: `engines/muscles/video_render/mcp/impl.py`
- [ ] Create `engines/muscles/video_render/mcp/spec.yaml`
- [ ] Create `engines/muscles/video_render/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `video.render.read` (READ, No-GC)
  - [ ] `video.render.write` (WRITE, GateChain)
  - [ ] `video.render.submit` (SUBMIT, GateChain)
  - [ ] `video.render.status` (STATUS, No-GC)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_video_render.py`)

### video_slowmo ✅
- **Wrapper Path**: `engines/muscles/video_slowmo/mcp/impl.py`
- [ ] Create `engines/muscles/video_slowmo/mcp/spec.yaml`
- [ ] Create `engines/muscles/video_slowmo/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `video.slowmo.read` (READ, No-GC)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_video_slowmo.py`)

### video_stabilise ✅
- **Wrapper Path**: `engines/muscles/video_stabilise/mcp/impl.py`
- [ ] Create `engines/muscles/video_stabilise/mcp/spec.yaml`
- [ ] Create `engines/muscles/video_stabilise/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `video.stabilise.read` (READ, No-GC)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_video_stabilise.py`)

### video_text ✅
- **Wrapper Path**: `engines/muscles/video_text/mcp/impl.py`
- [ ] Create `engines/muscles/video_text/mcp/spec.yaml`
- [ ] Create `engines/muscles/video_text/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `video.text.read` (READ, No-GC)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_video_text.py`)

### video_timeline ✅
- **Wrapper Path**: `engines/muscles/video_timeline/mcp/impl.py`
- [ ] Create `engines/muscles/video_timeline/mcp/spec.yaml`
- [ ] Create `engines/muscles/video_timeline/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `video.timeline.read` (READ, No-GC)
  - [ ] `video.timeline.write` (WRITE, GateChain)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_video_timeline.py`)

### video_visual_meta ✅
- **Wrapper Path**: `engines/muscles/video_visual_meta/mcp/impl.py`
- [ ] Create `engines/muscles/video_visual_meta/mcp/spec.yaml`
- [ ] Create `engines/muscles/video_visual_meta/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `video.visual.meta.read` (READ, No-GC)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_video_visual_meta.py`)

## AUDIO Lane
### audio_arrangement_engine ✅
- **Wrapper Path**: `engines/muscles/audio_arrangement_engine/mcp/impl.py`
- [ ] Create `engines/muscles/audio_arrangement_engine/mcp/spec.yaml`
- [ ] Create `engines/muscles/audio_arrangement_engine/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `audio.arrangement.engine.read` (READ, No-GC)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_audio_arrangement_engine.py`)

### audio_asr_whisper ⚠️ (Missing in Tree)
- **Wrapper Path**: `engines/muscles/audio_asr_whisper/mcp/impl.py`
- [ ] Create `engines/muscles/audio_asr_whisper/mcp/spec.yaml`
- [ ] Create `engines/muscles/audio_asr_whisper/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `audio.asr.whisper.read` (READ, No-GC)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_audio_asr_whisper.py`)

### audio_beat_features ⚠️ (Missing in Tree)
- **Wrapper Path**: `engines/muscles/audio_beat_features/mcp/impl.py`
- [ ] Create `engines/muscles/audio_beat_features/mcp/spec.yaml`
- [ ] Create `engines/muscles/audio_beat_features/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `audio.beat.features.read` (READ, No-GC)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_audio_beat_features.py`)

### audio_core ✅
- **Wrapper Path**: `engines/muscles/audio_core/mcp/impl.py`
- [ ] Create `engines/muscles/audio_core/mcp/spec.yaml`
- [ ] Create `engines/muscles/audio_core/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `audio.core.read` (READ, No-GC)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_audio_core.py`)

### audio_field_to_samples ✅
- **Wrapper Path**: `engines/muscles/audio_field_to_samples/mcp/impl.py`
- [ ] Create `engines/muscles/audio_field_to_samples/mcp/spec.yaml`
- [ ] Create `engines/muscles/audio_field_to_samples/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `audio.field.to.samples.read` (READ, No-GC)
  - [ ] `audio.field.to.samples.submit` (SUBMIT, GateChain)
  - [ ] `audio.field.to.samples.status` (STATUS, No-GC)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_audio_field_to_samples.py`)

### audio_fx_chain ✅
- **Wrapper Path**: `engines/muscles/audio_fx_chain/mcp/impl.py`
- [ ] Create `engines/muscles/audio_fx_chain/mcp/spec.yaml`
- [ ] Create `engines/muscles/audio_fx_chain/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `audio.fx.chain.read` (READ, No-GC)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_audio_fx_chain.py`)

### audio_groove ✅
- **Wrapper Path**: `engines/muscles/audio_groove/mcp/impl.py`
- [ ] Create `engines/muscles/audio_groove/mcp/spec.yaml`
- [ ] Create `engines/muscles/audio_groove/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `audio.groove.read` (READ, No-GC)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_audio_groove.py`)

### audio_harmony ✅
- **Wrapper Path**: `engines/muscles/audio_harmony/mcp/impl.py`
- [ ] Create `engines/muscles/audio_harmony/mcp/spec.yaml`
- [ ] Create `engines/muscles/audio_harmony/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `audio.harmony.read` (READ, No-GC)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_audio_harmony.py`)

### audio_hits ✅
- **Wrapper Path**: `engines/muscles/audio_hits/mcp/impl.py`
- [ ] Create `engines/muscles/audio_hits/mcp/spec.yaml`
- [ ] Create `engines/muscles/audio_hits/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `audio.hits.read` (READ, No-GC)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_audio_hits.py`)

### audio_ingest_local ⚠️ (Missing in Tree)
- **Wrapper Path**: `engines/muscles/audio_ingest_local/mcp/impl.py`
- [ ] Create `engines/muscles/audio_ingest_local/mcp/spec.yaml`
- [ ] Create `engines/muscles/audio_ingest_local/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `audio.ingest.local.read` (READ, No-GC)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_audio_ingest_local.py`)

### audio_ingest_local_file ⚠️ (Missing in Tree)
- **Wrapper Path**: `engines/muscles/audio_ingest_local_file/mcp/impl.py`
- [ ] Create `engines/muscles/audio_ingest_local_file/mcp/spec.yaml`
- [ ] Create `engines/muscles/audio_ingest_local_file/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `audio.ingest.local.file.read` (READ, No-GC)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_audio_ingest_local_file.py`)

### audio_ingest_remote_pull ⚠️ (Missing in Tree)
- **Wrapper Path**: `engines/muscles/audio_ingest_remote_pull/mcp/impl.py`
- [ ] Create `engines/muscles/audio_ingest_remote_pull/mcp/spec.yaml`
- [ ] Create `engines/muscles/audio_ingest_remote_pull/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `audio.ingest.remote.pull.read` (READ, No-GC)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_audio_ingest_remote_pull.py`)

### audio_loops ✅
- **Wrapper Path**: `engines/muscles/audio_loops/mcp/impl.py`
- [ ] Create `engines/muscles/audio_loops/mcp/spec.yaml`
- [ ] Create `engines/muscles/audio_loops/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `audio.loops.read` (READ, No-GC)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_audio_loops.py`)

### audio_macro_engine ✅
- **Wrapper Path**: `engines/muscles/audio_macro_engine/mcp/impl.py`
- [ ] Create `engines/muscles/audio_macro_engine/mcp/spec.yaml`
- [ ] Create `engines/muscles/audio_macro_engine/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `audio.macro.engine.read` (READ, No-GC)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_audio_macro_engine.py`)

### audio_mix_buses ✅
- **Wrapper Path**: `engines/muscles/audio_mix_buses/mcp/impl.py`
- [ ] Create `engines/muscles/audio_mix_buses/mcp/spec.yaml`
- [ ] Create `engines/muscles/audio_mix_buses/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `audio.mix.buses.read` (READ, No-GC)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_audio_mix_buses.py`)

### audio_mix_snapshot ✅
- **Wrapper Path**: `engines/muscles/audio_mix_snapshot/mcp/impl.py`
- [ ] Create `engines/muscles/audio_mix_snapshot/mcp/spec.yaml`
- [ ] Create `engines/muscles/audio_mix_snapshot/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `audio.mix.snapshot.read` (READ, No-GC)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_audio_mix_snapshot.py`)

### audio_pattern_engine ✅
- **Wrapper Path**: `engines/muscles/audio_pattern_engine/mcp/impl.py`
- [ ] Create `engines/muscles/audio_pattern_engine/mcp/spec.yaml`
- [ ] Create `engines/muscles/audio_pattern_engine/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `audio.pattern.engine.read` (READ, No-GC)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_audio_pattern_engine.py`)

### audio_performance_capture ✅
- **Wrapper Path**: `engines/muscles/audio_performance_capture/mcp/impl.py`
- [ ] Create `engines/muscles/audio_performance_capture/mcp/spec.yaml`
- [ ] Create `engines/muscles/audio_performance_capture/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `audio.performance.capture.read` (READ, No-GC)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_audio_performance_capture.py`)

### audio_preprocess_basic_clean ⚠️ (Missing in Tree)
- **Wrapper Path**: `engines/muscles/audio_preprocess_basic_clean/mcp/impl.py`
- [ ] Create `engines/muscles/audio_preprocess_basic_clean/mcp/spec.yaml`
- [ ] Create `engines/muscles/audio_preprocess_basic_clean/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `audio.preprocess.basic.clean.read` (READ, No-GC)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_audio_preprocess_basic_clean.py`)

### audio_render ✅
- **Wrapper Path**: `engines/muscles/audio_render/mcp/impl.py`
- [ ] Create `engines/muscles/audio_render/mcp/spec.yaml`
- [ ] Create `engines/muscles/audio_render/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `audio.render.read` (READ, No-GC)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_audio_render.py`)

### audio_resample ✅
- **Wrapper Path**: `engines/muscles/audio_resample/mcp/impl.py`
- [ ] Create `engines/muscles/audio_resample/mcp/spec.yaml`
- [ ] Create `engines/muscles/audio_resample/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `audio.resample.read` (READ, No-GC)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_audio_resample.py`)

### audio_sample_library ✅
- **Wrapper Path**: `engines/muscles/audio_sample_library/mcp/impl.py`
- [ ] Create `engines/muscles/audio_sample_library/mcp/spec.yaml`
- [ ] Create `engines/muscles/audio_sample_library/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `audio.sample.library.read` (READ, No-GC)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_audio_sample_library.py`)

### audio_segment_ffmpeg ⚠️ (Missing in Tree)
- **Wrapper Path**: `engines/muscles/audio_segment_ffmpeg/mcp/impl.py`
- [ ] Create `engines/muscles/audio_segment_ffmpeg/mcp/spec.yaml`
- [ ] Create `engines/muscles/audio_segment_ffmpeg/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `audio.segment.ffmpeg.read` (READ, No-GC)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_audio_segment_ffmpeg.py`)

### audio_semantic_timeline ✅
- **Wrapper Path**: `engines/muscles/audio_semantic_timeline/mcp/impl.py`
- [ ] Create `engines/muscles/audio_semantic_timeline/mcp/spec.yaml`
- [ ] Create `engines/muscles/audio_semantic_timeline/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `audio.semantic.timeline.read` (READ, No-GC)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_audio_semantic_timeline.py`)

### audio_separation ✅
- **Wrapper Path**: `engines/muscles/audio_separation/mcp/impl.py`
- [ ] Create `engines/muscles/audio_separation/mcp/spec.yaml`
- [ ] Create `engines/muscles/audio_separation/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `audio.separation.read` (READ, No-GC)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_audio_separation.py`)

### audio_service ✅
- **Wrapper Path**: `engines/muscles/audio_service/mcp/impl.py`
- [ ] Create `engines/muscles/audio_service/mcp/spec.yaml`
- [ ] Create `engines/muscles/audio_service/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `audio.service.read` (READ, No-GC)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_audio_service.py`)

### audio_shared ✅
- **Wrapper Path**: `engines/muscles/audio_shared/mcp/impl.py`
- [ ] Create `engines/muscles/audio_shared/mcp/spec.yaml`
- [ ] Create `engines/muscles/audio_shared/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `audio.shared.read` (READ, No-GC)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_audio_shared.py`)

### audio_structure_engine ✅
- **Wrapper Path**: `engines/muscles/audio_structure_engine/mcp/impl.py`
- [ ] Create `engines/muscles/audio_structure_engine/mcp/spec.yaml`
- [ ] Create `engines/muscles/audio_structure_engine/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `audio.structure.engine.read` (READ, No-GC)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_audio_structure_engine.py`)

### audio_timeline ✅
- **Wrapper Path**: `engines/muscles/audio_timeline/mcp/impl.py`
- [ ] Create `engines/muscles/audio_timeline/mcp/spec.yaml`
- [ ] Create `engines/muscles/audio_timeline/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `audio.timeline.read` (READ, No-GC)
  - [ ] `audio.timeline.write` (WRITE, GateChain)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_audio_timeline.py`)

### audio_to_video_origin ✅
- **Wrapper Path**: `engines/muscles/audio_to_video_origin/mcp/impl.py`
- [ ] Create `engines/muscles/audio_to_video_origin/mcp/spec.yaml`
- [ ] Create `engines/muscles/audio_to_video_origin/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `audio.to.video.origin.read` (READ, No-GC)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_audio_to_video_origin.py`)

### audio_voice_enhance ✅
- **Wrapper Path**: `engines/muscles/audio_voice_enhance/mcp/impl.py`
- [ ] Create `engines/muscles/audio_voice_enhance/mcp/spec.yaml`
- [ ] Create `engines/muscles/audio_voice_enhance/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `audio.voice.enhance.read` (READ, No-GC)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_audio_voice_enhance.py`)

### audio_voice_phrases ✅
- **Wrapper Path**: `engines/muscles/audio_voice_phrases/mcp/impl.py`
- [ ] Create `engines/muscles/audio_voice_phrases/mcp/spec.yaml`
- [ ] Create `engines/muscles/audio_voice_phrases/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `audio.voice.phrases.read` (READ, No-GC)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_audio_voice_phrases.py`)

## IMAGE Lane
### image_core ✅
- **Wrapper Path**: `engines/muscles/image_core/mcp/impl.py`
- [ ] Create `engines/muscles/image_core/mcp/spec.yaml`
- [ ] Create `engines/muscles/image_core/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `image.core.read` (READ, No-GC)
  - [ ] `image.core.write` (WRITE, GateChain)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_image_core.py`)

### typography_core ✅
- **Wrapper Path**: `engines/muscles/typography_core/mcp/impl.py`
- [ ] Create `engines/muscles/typography_core/mcp/spec.yaml`
- [ ] Create `engines/muscles/typography_core/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `typography.core.read` (READ, No-GC)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_typography_core.py`)

### vector_core ⚠️ (Missing in Tree)
- **Wrapper Path**: `engines/muscles/vector_core/mcp/impl.py`
- [ ] Create `engines/muscles/vector_core/mcp/spec.yaml`
- [ ] Create `engines/muscles/vector_core/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `vector.core.read` (READ, No-GC)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_vector_core.py`)

## CAD Lane
### boq_costing ✅
- **Wrapper Path**: `engines/muscles/boq_costing/mcp/impl.py`
- [ ] Create `engines/muscles/boq_costing/mcp/spec.yaml`
- [ ] Create `engines/muscles/boq_costing/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `boq.costing.read` (READ, No-GC)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_boq_costing.py`)

### boq_quantities ✅
- **Wrapper Path**: `engines/muscles/boq_quantities/mcp/impl.py`
- [ ] Create `engines/muscles/boq_quantities/mcp/spec.yaml`
- [ ] Create `engines/muscles/boq_quantities/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `boq.quantities.read` (READ, No-GC)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_boq_quantities.py`)

### cad_diff ✅
- **Wrapper Path**: `engines/muscles/cad_diff/mcp/impl.py`
- [ ] Create `engines/muscles/cad_diff/mcp/spec.yaml`
- [ ] Create `engines/muscles/cad_diff/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `cad.diff.read` (READ, No-GC)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_cad_diff.py`)

### cad_ingest ✅
- **Wrapper Path**: `engines/muscles/cad_ingest/mcp/impl.py`
- [ ] Create `engines/muscles/cad_ingest/mcp/spec.yaml`
- [ ] Create `engines/muscles/cad_ingest/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `cad.ingest.read` (READ, No-GC)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_cad_ingest.py`)

### cad_semantics ✅
- **Wrapper Path**: `engines/muscles/cad_semantics/mcp/impl.py`
- [ ] Create `engines/muscles/cad_semantics/mcp/spec.yaml`
- [ ] Create `engines/muscles/cad_semantics/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `cad.semantics.read` (READ, No-GC)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_cad_semantics.py`)

### cad_viewer ✅
- **Wrapper Path**: `engines/muscles/cad_viewer/mcp/impl.py`
- [ ] Create `engines/muscles/cad_viewer/mcp/spec.yaml`
- [ ] Create `engines/muscles/cad_viewer/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `cad.viewer.read` (READ, No-GC)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_cad_viewer.py`)

### plan_of_work ⚠️ (Missing in Tree)
- **Wrapper Path**: `engines/muscles/plan_of_work/mcp/impl.py`
- [ ] Create `engines/muscles/plan_of_work/mcp/spec.yaml`
- [ ] Create `engines/muscles/plan_of_work/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `plan.of.work.read` (READ, No-GC)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_plan_of_work.py`)

## TIMELINE Lane
### marketing_cadence ⚠️ (Missing in Tree)
- **Wrapper Path**: `engines/muscles/marketing_cadence/mcp/impl.py`
- [ ] Create `engines/muscles/marketing_cadence/mcp/spec.yaml`
- [ ] Create `engines/muscles/marketing_cadence/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `marketing.cadence.read` (READ, No-GC)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_marketing_cadence.py`)

### timeline_analyzer ✅
- **Wrapper Path**: `engines/muscles/timeline_analyzer/mcp/impl.py`
- [ ] Create `engines/muscles/timeline_analyzer/mcp/spec.yaml`
- [ ] Create `engines/muscles/timeline_analyzer/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `timeline.analyzer.read` (READ, No-GC)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_timeline_analyzer.py`)

### timeline_core ✅
- **Wrapper Path**: `engines/muscles/timeline_core/mcp/impl.py`
- [ ] Create `engines/muscles/timeline_core/mcp/spec.yaml`
- [ ] Create `engines/muscles/timeline_core/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `timeline.core.read` (READ, No-GC)
  - [ ] `timeline.core.write` (WRITE, GateChain)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_timeline_core.py`)

## 3D Lane
### animation_kernel ⚠️ (Missing in Tree)
- **Wrapper Path**: `engines/muscles/animation_kernel/mcp/impl.py`
- [ ] Create `engines/muscles/animation_kernel/mcp/spec.yaml`
- [ ] Create `engines/muscles/animation_kernel/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `animation.kernel.read` (READ, No-GC)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_animation_kernel.py`)

### material_kernel ⚠️ (Missing in Tree)
- **Wrapper Path**: `engines/muscles/material_kernel/mcp/impl.py`
- [ ] Create `engines/muscles/material_kernel/mcp/spec.yaml`
- [ ] Create `engines/muscles/material_kernel/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `material.kernel.read` (READ, No-GC)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_material_kernel.py`)

### mesh_kernel ⚠️ (Missing in Tree)
- **Wrapper Path**: `engines/muscles/mesh_kernel/mcp/impl.py`
- [ ] Create `engines/muscles/mesh_kernel/mcp/spec.yaml`
- [ ] Create `engines/muscles/mesh_kernel/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `mesh.kernel.read` (READ, No-GC)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_mesh_kernel.py`)

### scene_engine ⚠️ (Missing in Tree)
- **Wrapper Path**: `engines/muscles/scene_engine/mcp/impl.py`
- [ ] Create `engines/muscles/scene_engine/mcp/spec.yaml`
- [ ] Create `engines/muscles/scene_engine/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `scene.engine.read` (READ, No-GC)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_scene_engine.py`)

### solid_kernel ⚠️ (Missing in Tree)
- **Wrapper Path**: `engines/muscles/solid_kernel/mcp/impl.py`
- [ ] Create `engines/muscles/solid_kernel/mcp/spec.yaml`
- [ ] Create `engines/muscles/solid_kernel/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `solid.kernel.read` (READ, No-GC)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_solid_kernel.py`)

### stage_kernel ⚠️ (Missing in Tree)
- **Wrapper Path**: `engines/muscles/stage_kernel/mcp/impl.py`
- [ ] Create `engines/muscles/stage_kernel/mcp/spec.yaml`
- [ ] Create `engines/muscles/stage_kernel/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `stage.kernel.read` (READ, No-GC)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_stage_kernel.py`)

## CONTENT Lane
### creative ⚠️ (Missing in Tree)
- **Wrapper Path**: `engines/muscles/creative/mcp/impl.py`
- [ ] Create `engines/muscles/creative/mcp/spec.yaml`
- [ ] Create `engines/muscles/creative/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `creative.read` (READ, No-GC)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_creative.py`)

### page_content ⚠️ (Missing in Tree)
- **Wrapper Path**: `engines/muscles/page_content/mcp/impl.py`
- [ ] Create `engines/muscles/page_content/mcp/spec.yaml`
- [ ] Create `engines/muscles/page_content/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `page.content.read` (READ, No-GC)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_page_content.py`)

### seo ⚠️ (Missing in Tree)
- **Wrapper Path**: `engines/muscles/seo/mcp/impl.py`
- [ ] Create `engines/muscles/seo/mcp/spec.yaml`
- [ ] Create `engines/muscles/seo/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `seo.read` (READ, No-GC)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_seo.py`)

## OTHER Lane
### audio_normalise ✅
- **Wrapper Path**: `engines/muscles/audio_normalise/mcp/impl.py`
- [ ] Create `engines/muscles/audio_normalise/mcp/spec.yaml`
- [ ] Create `engines/muscles/audio_normalise/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `audio.normalise.read` (READ, No-GC)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_audio_normalise.py`)

### media ✅
- **Wrapper Path**: `engines/muscles/media/mcp/impl.py`
- [ ] Create `engines/muscles/media/mcp/spec.yaml`
- [ ] Create `engines/muscles/media/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `media.read` (READ, No-GC)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_media.py`)

### media_v2 ✅
- **Wrapper Path**: `engines/muscles/media_v2/mcp/impl.py`
- [ ] Create `engines/muscles/media_v2/mcp/spec.yaml`
- [ ] Create `engines/muscles/media_v2/mcp/impl.py` using `MUSCLE_SCOPE_TEMPLATES.md`
- [ ] Implement Scopes:
  - [ ] `media.v2.read` (READ, No-GC)
  - [ ] `media.v2.write` (WRITE, GateChain)
- [ ] Verify via Loader (add to `ENABLED_MUSCLES`)
- [ ] Add Tests (`test_wrapper_media_v2.py`)
