# Video/Audio Atomic Engines · Design Proposal

## Recap of relevant existing engines
- **Media upload (current)** — `engines/media/service/routes.py` provides `POST /media/upload` + `GET /media/stack`, storing a raw file in GCS via `GcsClient`, writing a `NexusDocument` with `asset_id` and URI. Media type is implicit; no durable metadata or links to derivatives.
- **Audio atoms** — `engines/audio/*` (ingest_local/local_file/remote_pull, preprocess_basic_clean, segment_ffmpeg, beat_features, asr_whisper stub) and `engines/audio_core` (pipeline with faster-whisper fallback, dataset builder, tiny LoRA trainer). All are CLI/runner functions; no HTTP wrappers yet.
- **Alignment/text/tagging/dataset** — `engines/align/audio_text_bars`, `engines/text/normalise_slang`, `engines/text/clean_asr_punct_case`, `engines/tag/flow_auto`, `engines/dataset/pack_jsonl`, `engines/train/*` (stubs). These assume local file paths and Pydantic IO models.
- **Video frame grab** — `engines/video/frame_grab` extracts stills via ffmpeg (auto interval or manual timestamps). Returns frame paths and timestamps; no asset linkage beyond the source URI.
- **Scene/Vector** — `engines/scene_engine` (scene build HTTP), `engines/nexus/vector_explorer` (vector ingest/query with GCS + Firestore), showing patterns for HTTP + Nexus/GCS persistence.

## Proposed atoms

### 1) Asset / Media Atom v2 (`engines/media_v2`)
Purpose: Typed media registry with durable metadata and lineage between original uploads and derived artifacts (segments, frames, stems, masks). HTTP-first, multi-tenant.

**Key entities**
- `MediaAsset`: {`id`, `tenant_id`, `env`, `user_id`, `kind` (video|audio|image|other), `source_uri`, `duration_ms`, `fps`, `audio_channels`, `sample_rate`, `codec_info`, `size_bytes`, `created_at`, `meta`}.
- `DerivedArtifact`: {`id`, `parent_asset_id`, `tenant_id`, `env`, `kind` (audio_segment|frame|stem|mask|render), `uri`, `start_ms`, `end_ms`, `track_label`, `meta`}.
- `DerivedArtifact.meta` now standardizes backend metadata for the new video atoms: `video_region_summary`, `visual_meta`, and `asr_transcript` artifacts automatically include `backend_version`, `model_used`, `cache_key`, and `duration_ms` (visual_meta also adds `frame_sample_interval_ms`). Media_v2 validation rejects registrations lacking `tenant_id`/`env` or attempting to bypass the `tenants/{tenant}/{env}/media_v2/{asset_id}/regions/{artifact_id}.png` prefix so downstream render/anonymise flows only reuse trusted files.
- `MediaUploadRequest`: multipart upload or remote URI reference; includes `kind` hint, optional `source_ref` (client-provided ID), and tags.

**HTTP endpoints (FastAPI router)**
- `POST /media-v2/assets` — upload (multipart) or JSON register; returns `MediaAsset` with `asset_id`. Extract and store basic probes (ffprobe when available). Stored via `GcsClient` or temp path under `tenant/media/{asset_id}/...`.
- `GET /media-v2/assets/{asset_id}` — fetch metadata + derived artifacts.
- `GET /media-v2/assets` — list/filter by `tenant_id`, `kind`, `tag`, `source_ref`.
- `POST /media-v2/assets/{asset_id}/artifacts` — register derived artifact (called by other engines, e.g., segmenter/frame_grab/render). Accepts `kind`, `uri` (local path or GCS), optional timing (`start_ms`, `end_ms`), track label, `meta`.
- `GET /media-v2/artifacts/{artifact_id}` — fetch artifact metadata (includes parent link).

**Storage/infra**
- Reuse `GcsClient` for blob paths; reuse `NexusDocument` or add Firestore collection for media metadata (storing type + probes + lineage). All writes tagged with `tenant_id`/`env` and `asset_id`.

### 2) Timeline / Project Atom (`engines/video_timeline`)
Purpose: Data-only representation of multi-track video/audio timelines with CRUD HTTP APIs; no heavy rendering logic.

**Key entities (all include `tenant_id`, `env`, `user_id`, timestamps)**
- `VideoProject`: {`id`, `title`, `description`, `tags`, `render_profile`, `sequences`: [ids], `meta`}.
- `Sequence`: {`id`, `project_id`, `name`, `duration_ms`, `timebase` (fps), `tracks`: [ids], `meta`}.
- `Track`: {`id`, `sequence_id`, `kind` (video|audio), `order` (stacking index), `muted`, `hidden`, `meta`}.
- `Clip`: {`id`, `track_id`, `asset_id`, `artifact_id` (optional, e.g., segment), `in_ms`, `out_ms`, `start_ms_on_timeline`, `speed`, `volume_db`, `opacity`, `meta`}.
- `Transition`: {`id`, `sequence_id`, `type` (crossfade, dip_to_black, wipe), `duration_ms`, `from_clip_id`, `to_clip_id`, `meta`}.
- `FilterStack`: {`id`, `target_type` (clip|track|sequence), `target_id`, `filters`: ordered list of {`type`, `params`, `enabled`}}; `filters` map later to ffmpeg graph nodes.

**HTTP endpoints**
- Projects: `POST/GET/PATCH /video/projects`, `GET /video/projects/{id}`.
- Sequences: `POST/GET/PATCH /video/projects/{project_id}/sequences`, `GET /video/sequences/{id}`.
- Tracks: `POST/GET/PATCH /video/sequences/{sequence_id}/tracks`, `GET /video/tracks/{id}`.
- Clips: `POST/GET/PATCH/DELETE /video/tracks/{track_id}/clips`, `GET /video/clips/{id}`.
- Transitions: `POST/GET/PATCH/DELETE /video/sequences/{sequence_id}/transitions`.
- Filters: `POST/GET/PATCH/DELETE /video/filter-stacks/{target_type}/{target_id}` (target type/id checked for consistency).

**Notes**
- Multi-track supported via ordered `Track` records; overlapping clips resolved at render-time rules.
- Keeps references to `asset_id`/`artifact_id` to tie back to media registry.

### 3) Render Atom (`engines/video_render`)
Purpose: Stateless render planner/executor that takes a timeline snapshot + render profile and produces a new rendered asset (video) plus registered artifact.

**Inputs**
- `RenderRequest`: {`tenant_id`, `env`, `user_id`, `project_id` or inline `SequenceSnapshot`, `render_profile` (`social_1080p_h264`, `preview_720p_fast`, `youtube_4k_h264`, `master_4k_prores`), `output_path` optional, `storage` target (local|gcs), `audio_mixdown` (stereo/mono), `watermark` optional}.
- Resolves assets/artifacts via Media Atom v2.

**Behavior**
- Build an ffmpeg plan: concatenation, track stacking with simple overlay filters, transitions (crossfade/dip_to_black mapping to xfade/fade), filter graphs from `FilterStack` (scaffold), resampling to profile (fps/resolution/codec).
- Uses render profiles for width/height/fps/codec/pix_fmt/bitrate/preset; supports dry-run (plan only) and execution with ffmpeg runner (timeouts/logging).
- Writes output to local path or GCS (`tenant/media/{new_asset_id}/render.mp4`).
- Registers the rendered output as a `DerivedArtifact` (`kind=render`) under Media Atom v2, returning new `asset_id`/`artifact_id`.

**HTTP endpoints**
- `POST /video/render` — accepts `RenderRequest`, builds an ffmpeg plan, executes when possible, registers rendered asset/artifact, returns `{asset_id, artifact_id, uri, profile, plan_preview}`.
- `POST /video/render/dry-run` — same input, but only returns the planned ffmpeg command/graph without execution.

### 4) HTTP Audio Service Atom (`engines/audio_service`)
Purpose: Thin HTTP wrapper exposing existing audio atoms as atomic endpoints, keyed by `asset_id` from Media Atom v2.

**Endpoints (all require `tenant_id`, `env`, `asset_id`, plus params)**
- `POST /audio/ingest` — register local/uploaded file as media asset (delegates to Media Atom v2; convenience).
- `POST /audio/preprocess` — body: `{asset_id, artifact_id? (raw), output_dir?, ffmpeg_opts?}` → runs `preprocess_basic_clean`, registers cleaned artifact(s) with `start_ms=0`.
- `POST /audio/segment` — `{asset_id, artifact_id?, segment_seconds, overlap_seconds}` → runs `segment_ffmpeg`, registers each segment as `DerivedArtifact(kind=audio_segment, start/end_ms)`; returns list with paths/URIs.
- `POST /audio/beat-features` — `{asset_id or artifact_ids[]}` → runs `beat_features`, returns bpm/downbeats/grid and registers artifacts with `meta.beat_features`.
- `POST /audio/asr` — `{asset_ids or artifact_ids[], model_name?, device?, compute_type?}` → uses `audio_core.asr_backend`; registers ASR JSON artifact (`kind=asr_transcript`) with timing data. Artifacts now carry `meta.backend_type`, `meta.requested_backend`, `meta.model_used`, `meta.duration_ms`, `meta.segment_count`, and `meta.cache_key` so downstream video renders and captions stash the lineage.
- `POST /audio/align` — `{asr_artifact_ids[], beat_meta?}` → runs `align/audio_text_bars` (or future beat-aware aligner); registers `bars` artifact.

**Notes**
- Each endpoint returns artifact IDs + URIs and persists lineage via Media Atom v2.
- CLI/runner usage remains unchanged; HTTP layer is additive.

### 5) Visual Meta Engine (`engines/video_visual_meta`)
Purpose: Cheap, structured “what’s on screen” summaries per video asset/artifact, emitted as `visual_meta` derived artifacts so agents can reason without decoding pixels.

**Models**
- `SubjectDetection`: `{track_id?, label, confidence, bbox_x/y/width/height}` with bbox normalized to [0,1].
- `VisualMetaFrame`: `{timestamp_ms, subjects[], primary_subject_center_x/y?, shot_boundary?}`.
- `VisualMetaSummary`: `{asset_id, artifact_id?, frames[], duration_ms?, frame_sample_interval_ms?}` stored as JSON in media_v2 (`DerivedArtifact(kind="visual_meta")`).

**HTTP endpoints**
- `POST /video/visual-meta/analyze` — body: `{tenant_id, env, user_id, asset_id, artifact_id?, sample_interval_ms=500, include_labels?, detect_shot_boundaries=true}`. Resolves the source (asset or artifact), runs the lightweight backend that emits a deterministic “wobble” for primary subject centers, writes a `visual_meta` JSON artifact (`meta.model_used="visual_meta_stub_v1"`), and returns `{visual_meta_artifact_id, uri, meta}`.
- `GET /video/visual-meta/{artifact_id}` — fetches and parses the stored `VisualMetaSummary`.
- `GET /video/visual-meta/by-clip/{clip_id}` — slices an existing `visual_meta` artifact for the clip’s in/out window; returns 404 if none exists for the clip’s asset.
- `POST /video/visual-meta/reframe-suggestion` — body: `{tenant_id, env, user_id, clip_id, target_aspect_ratio: "9:16"|"16:9"|"4:5"|"1:1", framing_style: "center"|"rule_of_thirds"}`. Returns suggested `ParameterAutomation` tracks for `position_x`, `position_y`, `scale` (keyframes aligned to the clip window) plus meta noting the source visual_meta artifact. Suggestions are not applied automatically.
- Visual meta artifacts now expose `meta.backend_version` and `meta.cache_key` so downstream services can determine whether to reuse existing artifacts or trigger a fresh analyze.

**Example artifact payload**
```json
{
  "asset_id": "a123",
  "artifact_id": "vf456",
  "frame_sample_interval_ms": 500,
  "frames": [
    {"timestamp_ms": 0, "subjects": [{"label": "frame_center", "confidence": 0.1, "bbox_x": 0.45, "bbox_y": 0.45, "bbox_width": 0.1, "bbox_height": 0.1, "track_id": "dummy_0"}], "primary_subject_center_x": 0.5, "primary_subject_center_y": 0.5, "shot_boundary": true},
    {"timestamp_ms": 500, "subjects": [], "primary_subject_center_x": 0.5, "primary_subject_center_y": 0.5, "shot_boundary": false}
  ],
  "duration_ms": 5000.0
}
```

**Reframe suggestion example**
```json
{
  "clip_id": "clip123",
  "automation": [
    {"property": "position_x", "target_type": "clip", "target_id": "clip123", "keyframes": [{"time_ms": 0, "value": 0.52}, {"time_ms": 500, "value": 0.61}]},
    {"property": "position_y", "target_type": "clip", "target_id": "clip123", "keyframes": [{"time_ms": 0, "value": 0.48}, {"time_ms": 500, "value": 0.55}]},
    {"property": "scale", "target_type": "clip", "target_id": "clip123", "keyframes": [{"time_ms": 0, "value": 1.1}, {"time_ms": 500, "value": 1.18}]}
  ],
"meta": {"source_visual_meta_artifact_id": "vf456", "target_aspect_ratio": "9:16"}
}
```

### Video regions, visual meta, and captions (Phase V01)
- `POST /video/regions` validates `RequestContext` vs payload, enforces `VIDEO_REGION_BACKEND` (default `opencv_face_detector`)/`VIDEO_REGIONS_MIN_CONFIDENCE`, caches results via `cache_key` and registers `video_region_summary` + mask artifacts under the enforced prefix `tenants/{tenant}/{env}/media_v2/{asset_id}/regions/`. The registered artifact metadata MUST include `backend_version`, `model_used`, `cache_key`; otherwise registration fails. This strict validation ensures downstream render/anonymise flows know exactly which detector generated the masks.
- `POST /video/visual-meta/analyze` (controlled by `VIDEO_VISUAL_META_BACKEND`) samples frames at `sample_interval_ms`, writes motion/shot/primary subject data, sets `frame_sample_interval_ms` in meta, and reuses the artifact whenever backend params + cache key match. Strict `RequestContext` validation is enforced to prevent cross-tenant access.
- `POST /video/captions/generate` uses the Whisper backend selected via `VIDEO_CAPTIONS_BACKEND` (defaulting to `stub` if missing). It enforces strict `RequestContext` validation, stores `asr_transcript` artifacts with `backend_version`/`model_used`/`language` metadata, and exposes rendered captions via `GET /video/captions/{artifact_id}/srt`.
- `POST /video/anonymise/faces` consumes the freshest `video_region_summary`, applies preset blur strengths, writes `face_blur` filters to the filter stack with `source_summary_id`/`backend_version` params, and short-circuits safely when no faces exist. It strict enforces tenant isolation.
- Render plans prefer the latest `video_region_summary`, `visual_meta`, and `asr_transcript`. Dry-runs (`POST /video/render/dry-run` → `POST /video/render`) log `dependency_notices` listing each upstream artifact with its `backend_version` + `cache_key`, making it trivial to audit which backends built downstream shots.
- Example flow (matches the Definition of Done):  
  1. `POST /video/regions` on the face fixture → obtains `video_region_summary`.  
  2. `POST /video/visual-meta/analyze` and `POST /video/captions/generate` to build summary/meta for the same asset.  
  3. `POST /video/anonymise/faces` + `POST /video/render/dry-run` + `POST /video/render`; `dependency_notices` reference the derived artifacts.  
  4. `GET /video/captions/{artifact_id}/srt` hydrates the final captions for delivery.

### 6) Audio Semantic Timeline (`engines/audio_semantic_timeline`)
Purpose: Structured timeline of speech/music/silence + coarse beats for a media asset, emitted as `audio_semantic_timeline` artifacts so video logic can reason without decoding audio.

**Models**
- `AudioEvent`: `{kind: speech|music|silence|other, start_ms, end_ms, speaker_id?, loudness_lufs?, confidence?, transcription?, meta?}`.
- `BeatEvent`: `{time_ms, bar_index?, beat_index?, subdivision?}`.
- `AudioSemanticTimelineSummary`: `{asset_id, artifact_id?, duration_ms?, events[], beats[], meta?}` stored as JSON (`DerivedArtifact(kind="audio_semantic_timeline")`). Each artifact’s `meta` now includes `model_used`, `backend`, `backend_version`, `backend_type`, `semantic_version`, `audio_semantic_cache_key`, `include_beats`, `include_speech_music`, `min_silence_ms`, `loudness_window_ms`, `speed_change_limit`, and the `backend_info` snapshot returned by `build_backend_health_meta`.

**HTTP endpoints**
- `POST /audio/semantic-timeline/analyze` — body: `{tenant_id, env, user_id?, asset_id, artifact_id?, include_beats=true, include_speech_music=true, min_silence_ms=300, loudness_window_ms=1000}`. Resolves asset or artifact, converts to wav as needed, and runs the configured backend (default `whisper_librosa` plus the environment overrides `AUDIO_SEMANTIC_WHISPER_MODEL`/`AUDIO_SEMANTIC_SEED`). The response emits `{audio_semantic_artifact_id, uri, meta}` where `meta` carries `cache_key`, `cache_hit`, `backend_info` (dependencies), and all artifact meta fields (including the deterministic `audio_semantic_cache_key = tenant_id|env|asset_id|artifact_id|include_beats|include_speech_music|min_silence_ms|loudness_window_ms|backend_version|user_id`). When dependencies are missing the stub backend runs (`meta.backend_type="stub"` and `meta.semantic_version="audio_semantic_stub_v1"`), but downstream callers still see a well-formed artifact with consistent meta.  
- `GET /audio/semantic-timeline/{artifact_id}` — fetch/parse the stored summary.  
- `GET /audio/semantic-timeline/by-clip/{clip_id}` — slices events and beats to the clip window, returns them in **clip-relative** milliseconds, and the summary meta sets `clip_window_ms`, `clip_relative=true`, `speed_change_limit=1.05`, `speed_change=clip.speed`, and `speed_change_limited` (true when a rate change was requested).  

- Render plan meta now includes `audio_semantic_sources` when semantic artifacts are present, `dependency_notices` list every regions/visual_meta/captions artifact along with their `backend_version` + `cache_key`, and `audio_to_video_origin` reads the same semantic artifacts to nudge shot start/duration toward the first speech event. Each generated `VideoShot.meta` now carries `semantic_version`, `semantic_cache_key`, and `semantic_offset_ms`, and the corresponding `ShotListResult.meta` echoes the cache key/version so downstream layers know exactly which semantic artifact influenced the shot list.

**Example artifact payload**
```json
{
  "asset_id": "a123",
  "duration_ms": 60000,
  "events": [
    {"kind": "speech", "start_ms": 0, "end_ms": 5000, "loudness_lufs": -20.0},
    {"kind": "silence", "start_ms": 5000, "end_ms": 5800},
    {"kind": "music", "start_ms": 5800, "end_ms": 13800}
  ],
  "beats": [
    {"time_ms": 0, "beat_index": 0, "bar_index": 0},
    {"time_ms": 500, "beat_index": 1, "bar_index": 0}
  ],
  "meta": {"model_used": "audio_semantic_stub_v1", "backend_version": "audio_semantic_stub_v1", "audio_semantic_cache_key": "asset|..."}
}
```

- Render plan meta includes `audio_semantic_sources` when semantic artifacts are present, paving the way for smarter ducking/pacing later, and now also surfaces `dependency_notices` that list every regions/visual_meta/captions artifact along with their `backend_version` + `cache_key` for dry-run auditing.
- `audio_to_video_origin` reads these same artifacts to nudge shot start/duration toward the first speech event (semantic offsets are logged as `meta.semantic_offset_ms` on each `VideoShot`), while still preserving any `source_*` metadata from the original audio artifacts.

### V02 FX & transition catalog
#### Filter catalog
| Filter | Description | Parameter clamps | Mask-aware |
| --- | --- | --- | --- |
| `sharpen` | Detail boost via `unsharp`. | `luma_x/y` 1–20, `luma_amount` 0–5 | No |
| `vignette` | Corner falloff. | `angle` 0–1, `softness` 0.1–1, `strength` 0.1–1 | No |
| `hue_shift` | Hue rotation. | `shift` -180..180° | No |
| `film_grain` | Add noise. | `strength` 0–50 | No |
| `gamma` | Gamma correction. | `gamma` 0.1–6 | No |
| `bloom` | Glow via `boxblur`. | `intensity` 0–1, `radius` 2–60 | No |
| `levels` | Brightness/contrast/gamma blend. | `black` 0–0.5, `white` 0.5–1, `gamma` 0.1–6 | No |
| `teeth_whiten`, `skin_smooth`, `eye_enhance`, `face_blur` | Region-aware grades. | Inputs 0–1 map to brightness/blur/contrast; `face_blur` uses `strength` 0.1–1. | Yes (clip mask or region summary) |
| `lut` | 3D LUT via path or artifact id. | Requires `lut_path` or `lut_artifact_id`. | Optional |
> `video_render` builds each expression through `_build_filter_expression`, clamps parameters, and replays region-aware filters through `resolve_region_masks_for_clip`. When a mask exists the engine splits the stream, applies the filter, merges via `alphamerge`, and overlays back so everything stays deterministic.

#### Transition catalog
| Transition | Video alias | Audio alias | Notes |
| --- | --- | --- | --- |
| `crossfade` | `fade` | `acrossfade` | Standard dissolve. |
| `dip_to_black` | `fadeblack` | `acrossfade` | Fade in/out through black. |
| `dip_to_white` | `fadewhite` | `acrossfade` | Fade in/out through white. |
| `wipe_left` | `wipeleft` | `acrossfade` | Leftwards horizontal wipe. |
| `wipe_right` | `wiperight` | `acrossfade` | Rightwards wipe. |
| `push_left` | `slideleft` | `acrossfade` | Slide new clip from right. |
| `push_right` | `slideright` | `acrossfade` | Slide new clip from left. |
| `slide_up` | `slideup` | `acrossfade` | Vertical upward slide. |
| `slide_down` | `slidedown` | `acrossfade` | Vertical downward slide. |
> `build_transition_plans` sorts transitions by `start_ms` and `id`, clamps durations, and records the alias pair in `meta.transitions` so automation layers can match `video_alias`/`audio_alias` back to ffmpeg.

#### Render profile table
| Profile | Resolution | FPS | Video codec | Audio codec + bitrate | Description |
| --- | --- | --- | --- | --- | --- |
| `draft_480p_fast` | 854×480 | 24 | `libx264` | `aac` 96k | Low-res draft export for quick iterations. |
| `preview_720p_fast` | 1280×720 | 30 | `libx264` | `aac` 128k | Fast preview tuned for CPU/GPU. |
| `social_1080p_h264` | 1920×1080 | 30 | `libx264` | `aac` 192k | Balanced social export. |
| `youtube_4k_h264` | 3840×2160 | 30 | `libx264` | `aac` 320k | High-bitrate YouTube master. |
| `master_4k_prores` | 3840×2160 | 30 | `prores_ks` | `pcm_s16le` | ProRes master with uncompressed audio. |
> Profiles publish `threads`, `preset`, `audio_sample_rate`, and `audio_channels` so render arguments match the hardware target. `render_profile_description` surfaces in plan meta alongside `render_profile`, letting callers know why a specific profile was chosen.

#### Example two-clip timeline
1. Clip A (A-roll) and Clip B (B-roll) overlap by 500ms; Clip A carries a `vignette` filter, Clip B opts into `slowmo_quality=medium` with `optical_flow=True`.  
2. Filter graph snippet becomes `...vignette...; [0:v][1:v]xfade=transition=fade:duration=0.500:offset=0`. Slowmo injects `minterpolate=fps=30:mi_mode=mci:mc_mode=aobmc:me_mode=bilin`.  
3. Plan meta includes `transitions[0].video_alias == "fade"`/`audio_alias == "acrossfade"`, `slowmo_details[0].method == "minterpolate"`, `slowmo_details[0].preset_description == "Balanced optical flow with moderate interpolation"`, and `render_profile_description == "1080p H.264 for social delivery with balanced quality"`.  
4. Missing masks or summaries surface as `warnings` (`video_regions missing for asset ...`) and `dependency_notices` list each `video_region_summary`, `visual_meta`, and `captions` artifact with its `backend_version` + `cache_key`, guaranteeing deterministic reuse. `stabilise_details` records smoothing/zoom/crop/tripod per clip while `stabilise_warnings` calls out missing transforms so clients can reroute or request a manual pass.

### Assist + focus automation pipelines
- `video_assist` now supervises highlight generation by combining `audio_semantic_timeline` events with `visual_meta` motion/subject scores. Highlights are cached per `(project_id,target_duration)` so repeated calls reuse computed plans, and returned tracks carry `meta.highlight_score_version` plus the pacing preset that produced them (`fast|medium|slow`). When no semantic/visual data exists it logs the fallback and still emits deterministic middle-of-asset clips.
- `video_focus_automation` consumes the same artifacts: it loads cached JSON payloads (preferring metadata in `DerivedArtifact.meta`), merges speech windows with sampled subject centers, and writes `ParameterAutomation` keyframes that hold each detected center for the duration of the speech event. Missing artifacts drop into a logged center fallback instead of random drift.

### 7) Video Effects & Presets
Purpose: Make everyday edit moves data-driven (no one-offs) via blend modes, overlays, reusable filter/motion presets, and explicit speed semantics.

**Blend modes + film burns**
- `Clip.blend_mode`: `normal|add|screen|multiply|overlay` (defaults to `normal`). Render maps to ffmpeg blend/overlay; `add` and `screen` are live, others are scaffolded.
- Film burn pattern: put a burn clip on a higher track, set `blend_mode="screen"` or `"add"`, and optionally stack a `FilterStack` to tint/brighten. Masks/filter stacks continue to apply as normal.

**Filter presets (`engines/video_presets`)**
- Model: `FilterPreset {id, tenant_id, env, name, description?, filters[], tags[], meta?}` reuses `Filter` shape from `FilterStack`.
- HTTP: `POST/GET/GET by id/DELETE` under `/video/presets/filters`. Tenants store/reuse preset filters, then UI/agents copy them into clip/track/sequence filter stacks (no auto-apply).

**Motion presets (shake)**
- Model: `MotionPreset {id, tenant_id, env, name, description?, duration_ms, tracks: [ParameterAutomation], tags[], meta?}`.
- Built-ins: `shake_1/2/3` exposed via `/video/presets/motion` (tagged `built_in`), each a small jitter automation on `position_x/position_y`. Endpoints mirror filter presets (`POST/GET/list/DELETE`).
- Consumers copy the automation tracks onto clips; presets are definitions only.

**Speed / slow-mo semantics**
- `Clip.speed` (default `1.0`) now influences render: effective clip duration scales by `1/speed`, and video setpts are applied in-plan (`setpts=PTS/<speed>`). `speed>1` fast-forwards, `speed<1` slow-mo. Audio currently follows the same rate (pitch-preserving time-stretch can be added later).

- **Transition metadata**: Each transition records `meta.transitions` (`type`, `order`, `start_ms`, `duration_ms`, `video_alias`, `audio_alias`) so agents/UI flows can deterministically align overlays or ParameterAutomation to the render plan. All supported transitions map to deterministic `xfade`/`acrossfade` pairs.
- **Slowmo / stabilise metadata**: Slowmo quality (`high`/`medium`/`fast`) writes `meta.slowmo_details` (method, quality, FPS) and falls back to `tblend` when optical flow is missing; missing stabilise transforms emit `meta.stabilise_warnings` instead of silently skipping.
- **Profile defaults**: Built-in filter presets now include `profile_default_<render_profile>` entries per profile with `meta.render_profiles`, letting orchestrators auto-suggest or apply grade defaults for the active render profile.

### 8) Voice Enhance Engine (`engines/audio_voice_enhance`)
Purpose: Produce `audio_voice_enhanced` artifacts for cleaner/more present dialog, reusable across audio/video flows.

**Models**
- `VoiceEnhanceRequest`: `{tenant_id, env, user_id?, asset_id, artifact_id?, mode: default|podcast|vlog|phone_recording, target_speaker_id?, aggressiveness (0-1), preserve_ambience}`.
- `VoiceEnhanceResult`: `{artifact_id, uri, meta}`.

**Behavior (stub v1)**
- Backend: ffmpeg-only chain (highpass/lowpass/compressor/presence EQ/noise reduction), `model_used="voice_enhance_ffmpeg_stub_v1"`.
- Registers `DerivedArtifact(kind="audio_voice_enhanced")` with meta `{mode, aggressiveness, preserve_ambience, model_used, backend_version, voice_enhance_cache_key}`. Cache key: `asset_id|artifact_id|mode|aggressiveness|preserve_ambience|backend_version`; identical requests reuse existing artifacts.

**HTTP endpoints**
- `/audio/voice-enhance` (engine router and via `audio_service`) — POST accepts `VoiceEnhanceRequest`, returns `VoiceEnhanceResult`. `GET /audio/voice-enhance/{artifact_id}` fetches metadata.

**Render hook**
- `RenderRequest` flags: `use_voice_enhanced_audio`, `voice_enhance_mode?`, `voice_enhance_if_available_only` (default True).
- When enabled, render searches for `audio_voice_enhanced` artifacts per asset (mode-matched if provided) and includes them as preferred audio sources; if missing and `voice_enhance_if_available_only=False`, plan meta surfaces a warning. No automatic enhancement run during render; treat enhancement as a pre-pass.
- Plan meta surfaces `audio_voice_enhance_selection` (per-clip source choice) and `voice_enhance_warnings` when requested artifacts are absent.
- `Track.audio_role` (dialogue|music|fx|ambience|generic) guides audio selection; dialogue/generic tracks prefer enhanced audio when requested, music/fx/ambience stay on original.

## Implemented HTTP prefixes
- Media v2: `/media-v2/*`
- Timeline/Project: `/video/projects`, `/video/sequences`, `/video/tracks`, `/video/clips`, `/video/transitions`, `/video/filter-stacks`
- Render: `/video/render`, `/video/render/dry-run`
- Audio service: `/audio/preprocess`, `/audio/segment`, `/audio/beat-features`, `/audio/asr`, `/audio/align`

## Video Quality vNext – Current state
- **Transforms/masks**: Clips carry `scale_mode`, `position`, `crop`, `mask_artifact_id`; render resolves masks and applies `alphamerge` + overlay stacking. VideoAnonymise now consumes `video_region_summary` entries, skips blur when no faces exist, and tags newly added `face_blur` filters with the detector `backend_version`. The `video_region_summary` artifacts themselves record `meta.backend_version` and `meta.cache_key` so downstream renders know which mask cache they reused.
- Mask artifacts are single-channel (L mode) PNGs with `meta.feather_radius`, `meta.selection_hash`, `meta.mask_type`, and counts for points/strokes; video_render/video_mask use those fields to deduplicate reused masks and ensure alpha merges remain deterministic.
- **Effects catalog**: Render plans now honor sharpen, vignette, hue_shift, film_grain, bloom, gamma, and levels filters (within `render_plan.filters`) while rejecting unknown types up front; LUTs still resolve artifact IDs when provided.
- **Transition graphs**: Crossfade/dip/wipe/push transitions all map to deterministic `xfade`/`acrossfade` filters and surface their durations so UI agents can reason about ordering.
- **Slow motion & stabilise metadata**: Rendering records `slowmo_details` describing the selected quality and mode (minterpolate vs tblend) plus `stabilise_warnings` when transforms are missing; high/medium slowmo use optical-flow presets while `fast` or missing flow falls back to `tblend`.
- **Profiles**: Render profiles (`social_1080p_h264`, `preview_720p_fast`, `youtube_4k_h264`, `master_4k_prores`) drive width/height/fps/codec/pix_fmt/bitrate/preset.
- **Transitions**: Model supports `crossfade`, `dip_to_black/white`, `wipe_left/right`, `push_left/right`; render maps to ffmpeg `xfade` variants + `acrossfade`.
- **Filters**: FilterStack supports exposure/contrast/saturation/temperature/tint/lut; render maps to `eq`/`hue`/`curves`/`lut3d` in-order per target (clip/track/sequence).
- **Automation**: `ParameterAutomation` + `Keyframe` models allow animating `position_x/position_y/scale/opacity/volume_db`; render derives simple expressions for volume/position (placeholders improving fidelity).
- **Audio**: Clip `volume_db`, fades, normalize hook (`normalize_audio`/`target_loudness_lufs`), ducking hook, and automation-driven volume filters included in plan.
- **Proxy ladder**: `ensure_proxies_for_project` now synthesizes `/video_proxy_360p` and `/video_proxy` derivatives when missing, stores `proxy_cache_key` metadata, tags each artifact with its proxy resolution, source asset, profile, and the hardware encoder used for that transcode.
- **Render metadata / preview warnings**: Every `RenderPlan` carries `hardware_encoder`, `source_assets`, and preview plans annotate `preview_warnings` (`no_tracks_for_preview`, `no_clips_for_preview`) plus the draft profile chosen (`draft_480p_fast` for DRAFT strategies). This metadata is now mirrored on the registered render artifacts for downstream agents and audit tooling.
- **Job/backpressure guard**: Chunk renders attach explicit `stage_timeout` metadata (default 90s via `VIDEO_RENDER_CHUNK_TIMEOUT`); the job queue honors `VIDEO_RENDER_MAX_CONCURRENT_JOBS` (default 4) and refuses to enqueue more than that many queued/running jobs per tenant, so Preview orchestrators can throttle dispatch without silent failures.

## Render jobs and caching
- **Job model**: `VideoRenderJob` (queued/running/succeeded/failed/cancelled) with progress, plan snapshot, result asset/artifact ids, error message, and `render_cache_key`.
- **Job API**: `POST /video/render/jobs` (create + optional cache hit), `GET /video/render/jobs/{id}`, `GET /video/render/jobs`, `POST /video/render/jobs/{id}/run`, `POST /video/render/jobs/{id}/cancel`.
- **Execution**: `run` endpoint executes render synchronously, updates progress/status, and registers outputs via media_v2.
- **Caching**: Cache key (project_id + render_profile + project updated_at) stored on jobs and render artifacts; job creation reuses prior succeeded job/artifact when cache key matches.

## Chunked Rendering & Loudness
- **Segment model**: `RenderSegment` captures `{id, tenant_id, env, project_id, sequence_id, segment_index, start_ms, end_ms, overlap_ms, profile, cache_key}`. Derived artifacts use `kind="render_segment"` with the same metadata.
- **Planning**: `POST /video/render/chunks/plan` returns linear segments across the sequence using `segment_duration_ms` (default 15s) plus boundary padding `overlap_ms` (default ~750ms). Overlap is applied on both sides to preserve transitions.
- **Segment jobs**: `POST /video/render/jobs/segments` accepts a base `RenderRequest` + segment list and creates queued jobs (type `segment`); `POST /video/render/jobs/chunked` combines planning + job creation in one call. Cache keys include profile, timeline updated_at, normalize flags, and the segment window.
- **Segment rendering**: Segment render plans window clips/transitions to `[start_ms-overlap_ms, end_ms+overlap_ms]`, emit `render_segment` artifacts with timing metadata, and support dry-run for safe planning.
- **Stitching**: `POST /video/render/chunks/stitch` trims overlaps, concatenates segment artifacts with ffmpeg, optionally applies master loudness, and registers a final `render` artifact with cache metadata + source job IDs.
- **Loudness normalization v1**: `RenderRequest.normalize_audio` + `target_loudness_lufs` insert a master `loudnorm` filter (`I=target, TP=-1.5, LRA=11, dual_mono=true`) into the audio chain. Cache keys incorporate loudness parameters; dry-run plans surface the applied filter.

## Persistence & ffmpeg notes (current wiring)
- **Firestore/Nexus patterns**: existing Firestore backend (`engines/nexus/backends/firestore_backend.py`) uses collections suffixed by tenant (e.g., `nexus_snippets_{tenant}`) and stores `tenant_id`/`env` on each document. Media_v2 and video_timeline now default to Firestore-backed repositories when the client is available; otherwise they fall back to in-memory repos for local/tests. Collections are per-tenant (`media_assets_{tenant}`, `media_artifacts_{tenant}`, `video_*_{tenant}`) with env stored on each document.
- **GCS**: `GcsClient` prefixes uploads as `tenant/media/...` (raw bucket) and is used by media_v2 uploads, audio_service outputs, and render outputs when `storage_target="gcs"`. If GCS is unavailable, services fall back to local temp paths.
- **ffmpeg**: Existing engines call ffmpeg via `subprocess` (`video/frame_grab`, `audio/segment_ffmpeg`). Render Atom builds an ffmpeg plan and executes it via `engines/video_render/ffmpeg_runner.py` with enforced output dirs, timeouts, and error propagation; dry-run mode returns the planned command without executing. Render profiles cover 720p preview → 4K h264/prores.

## Example flows
- **Upload → timeline → render**:
  1) `POST /media-v2/assets` (multipart) to ingest a video; receive `asset_id`.
  2) `POST /video/projects` then add sequence/track/clip referencing `asset_id`.
  3) `POST /video/render` (or `/video/render/dry-run` to inspect the plan); receive `asset_id`/`artifact_id` for the rendered output (uploaded to GCS if configured).
- **Mask generation**:
  - `POST /video/masks/auto` with a `MaskRequest` (point/box prompt) → registers `mask` artifact via media_v2; `GET /video/masks/{artifact_id}` fetches metadata.
- **Masked render**:
  - Clips may include `mask_artifact_id`; render plan will include mask inputs and alpha/overlay usage in the filtergraph during dry-run/execute.
- **Audio processing via HTTP**:
  1) Ingest audio via `/media-v2/assets`.
  2) `POST /audio/preprocess` → register `audio_clean` artifact.
  3) `POST /audio/segment` → register `audio_segment` artifacts.
  4) `POST /audio/beat-features` → store beat metadata per artifact.
  5) `POST /audio/asr` → register `asr_transcript` artifacts (faster-whisper when installed).
  6) `POST /audio/align` → register `bars` artifact for captions/beat-driven edits.

## Typography overlays
- `VideoTextService` now reuses `typography_core` to render text; every response includes axis metadata (`variant_axes`), `tracking`, and a `layout_hash` so downstream render plans can deduplicate overlays.
- `ImageLayer` text props expose `text_preset`, `text_tracking`, and `text_variation_settings`; the backend forwards those to typography_core so video/image editors share the same styling rules.
- This shared pipeline keeps font resolution deterministic (axis clamping + presets) and surfaces metadata for telemetry/caching when overlayed assets are used in renders.
- Vector overlays coming from `vector_core` scenes rasterize via `image_core` and can be blended onto video previews just like image layers; their transforms/stroke opacity are applied by the same renderer, so transparent/rotated shapes reuse the same compositing paths as typography overlays. 
- Vector artifacts now emit `layout_hash` + `boolean_ops` metadata so render caching or video preview pipelines can detect reused overlays instead of rerendering.

### 9) Multicam Atom (`engines/video_multicam`)
Purpose: Manage multi-camera sessions, providing deterministic audio-based alignment and automated cutting.

**Models**
- `MultiCamSession`: {`id`, `tenant_id`, `tracks` (asset_id, role, offset_ms), `base_asset_id`}.
- `MultiCamAlignResult`: {`session_id`, `offsets_ms`, `meta` (confidences, cache_hit)}.

**Behavior**
- **Alignment**: `POST /video/multicam/sessions/{id}/align` uses `waveform_cross_correlation` (via librosa/scipy) to calculate lags relative to a base asset.
- **Confidence**: Returns `confidences` (0-1) in metadata based on correlation peak energy.
- **Caching**: Results cached in `session.meta.alignment_cache` keyed by method/version/search_window; identical requests return cached offsets instantly.
- **Auto-Cut**: `POST /.../auto-cut` uses visual motion + audio semantic energy to generate a program sequence.
- **Security**: Strict `tenant_id` and `env` enforcement on all endpoints.

## Ops notes
- **Dependencies**: ffmpeg installed and on PATH; optional faster-whisper/librosa/torch improve ASR/beat features but endpoints degrade gracefully. Firestore client + credentials (or emulator) required for persistent repos; otherwise in-memory fallback. GCS buckets configured via `RAW_BUCKET`/`DATASETS_BUCKET` for uploads; otherwise local temp storage is used.
- **Env**: ensure `TENANT_ID`/`ENV` available when using Firestore default repos; HTTP requests still require explicit `tenant_id`/`env`.

## Tenant/env/user handling standard (for new engines)
- **Fields**: use snake_case everywhere: `tenant_id`, `env`, `user_id`. All three required on HTTP requests; `env` defaults allowed only via config (`runtime_config.get_env()`) when explicitly marked optional.
- **Models**: shared `RequestContext` Pydantic model in a small utility module (e.g., `engines/common/identity.py`) with validators for `tenant_id` pattern `^t_[a-z0-9_-]+$`, `env` in {dev, stage, prod}, optional `user_id`.
- **Persistence**: every stored record (media asset, artifact, project, clip, render result) must include `tenant_id` and `env`; storage paths prefix with `tenant_id`.
- **Defaults**: avoid `t_unknown` in new HTTP surfaces; reject requests missing `tenant_id`. Tests can pass `t_test`.
- **Logging**: `DatasetEvent` and Nexus writes carry the same `tenant_id`/`env`/`user_id` for traceability.

## How the atoms support apps
- **CapCut-style editor**: Media Atom v2 ingests camera rolls and keeps probes + artifacts; Timeline Atom stores multi-track edits with filters/transitions; Render Atom produces 1080p/30 exports (registered as new assets); Audio Service wraps ingest → clean → segment → ASR → alignment to generate captions/beat grids that can be overlaid or drive transitions.
- **Future apps**: The same atoms allow agents to suggest clip trims (Timeline updates), swap audio stems (new artifacts), auto-generate captions from ASR artifacts, or auto-cut to beat grids; rendered outputs become new assets that feed back into Vector Explorer or other downstream engines.
