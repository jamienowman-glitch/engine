# Video/Audio Editor Muscle – Master Implementation Plan (P0–P15)

Scope: backend-only engines that power the video/audio editor stack (media_v2, video_timeline, video_render, video_mask, video_regions, video_anonymise, video_visual_meta, video_multicam, video_text, video_presets, audio_service, audio_voice_enhance, audio_semantic_timeline, and new edit-centric engines below). Out of scope: 3D/HAZE/CAD/spine/auth/RequestContext/Firestore layouts/S3 wiring/connectors/UI. If tenant/user scoping appears, leave `# NOTE: tenant/user scoping deferred – will integrate with core spine later.` and proceed with pure engine logic.

Execution principle: Treat phases as a single conveyor belt—finish the exit criteria, then roll immediately into the next phase. Do not pause between phases for design rework; keep APIs stable unless explicitly marked as “CONTRACT CHANGE”.

---

## P0 – Core Media, Timeline, Render (1080p backbone)
- Entry: media_v2, video_timeline, video_render exist; stabilize them.
- Implementation: harden ffmpeg availability checks; verify chunked render + stitch for multi-minute 1080p; validate loudnorm and audio routing; add smoke assets + golden-plan fixtures; ensure render jobs register artifacts in media_v2 with cache keys.
- Production bar: all timeline/render tests green; render reliable on multi-minute 1080p with chunking; deterministic dry-run plans.

## P1 – Titles, Presets, Shake, Speed (editor feel)
- Implementation: finish video_text → render mapping (fonts/styles → overlays); lock colour/motion presets in video_presets (shake_1/2/3 built-ins); enforce speed-aware setpts + duration math in render; add tests for preset application and title overlays.
- Production bar: preset + title coverage in tests; speed math stable; docs updated under docs/engines/.

## P2 – Masks, Regions, Visual Meta, Voice Enhance (compositing + clarity)
- Implementation: upgrade video_mask + video_regions backends to real OpenCV/ONNX paths with deterministic fixtures; wire masks/regions into render filtergraphs; promote video_anonymise helper to use real detectors; ensure video_visual_meta emits cached artifacts and clip slices; swap audio_voice_enhance backend to a real model (or deterministic DSP chain) and expose via audio_service + render hook; integrate audio_semantic_timeline outputs into plan meta.
- Production bar: deterministic tests with small sample videos; artifacts registered in media_v2; render integration verified for masks/regions/voice-enhance.

### Phase 3: Multicam & Smart Audio (P3)
- [x] **Audio Cross-Correlation Sync** (`engines/video_multicam`)
  - [x] Use `librosa`/`scipy` for finding lag between audio tracks.
  - [x] Update `MultiCamAlignBackend` to use DSP.
- [x] **Smart Auto-Cut Heuristics** (`video_multicam`)
  - [x] Use `audio_semantic_timeline` (loudness/speech events) to switch cameras.
  - [x] "If current cam silent & other cam loud -> Switch".
- [x] **Smart Ducking** (Render)
  - [x] Render engine applies volume automation to music tracks when speech maps to active time windows.
  - [x] "Radio Style" auto-mixing. tests with 2–3 cameras and bounded sync error.
- Production bar: reproducible multicam sync + auto-cut; ducking behaviour validated with fixtures.

## P4 – Slow-Mo, Stabilisation, Proxies (handheld-friendly)
- Implementation: introduce slow-mo engine (optical flow interpolation) and render hook for clip-level speed+interp; add stabilization engine (feature tracks → smooth → crop) with filter-level integration; build proxy generator engine and mark proxy vs full-res in timeline/render selection; cover perf envelopes with medium-length clips.
- Production bar: slow-mo/stabilization/proxy flows tested on realistic samples; render selects proxies when requested; performance bounds documented.

## P5 – Captioning & Smart Assist (audio ↔ visual loop)
- Implementation: ship video_captions engine with HTTP: `POST /video/captions/generate` (ASR-driven tracks) and `POST /video/captions/burn-in` (render overlay); make timeline/render caption-aware; add highlight-reel helper using audio_semantic_timeline + visual_meta to flag “interesting” spans; deterministic fixtures for timing/positioning.
- Production bar: caption generation/burn-in tested; highlight-reel outputs stable given metadata.

## P6 – Effect Stacking & Dependency Graph (stable chains)
- Implementation: add effect_graph engine to represent filter stacks as DAGs (colour/blur/masks/overlays/text nodes); compiler to ffmpeg filtergraph with deterministic ordering; validation to catch cycles/conflicts (e.g., colour space clashes); expose graph usage from timeline/render (no breaking change—keep flat stacks as a compatibility path).
- Production bar: same graph → same filtergraph; conflict detection covered by tests.

## P7 – Template Sequence Engine (reusable recipes)
- Implementation: build video_edit_templates engine (data-driven templates: import assets → create sequence/tracks → add clips with positions → apply effects/transitions); `apply_template(template_id, assets)` returns ready timeline; add validation to avoid overlaps; library + HTTP surface.
- Production bar: templates applied in tests produce valid, non-overlapping timelines; deterministic outputs.

## P8 – Region-Aware Audio-Visual Coupling (focus automation)
- Implementation: helpers to join audio_semantic_timeline + video_visual_meta (e.g., `find_visual_focus_during_speech`); generate automation curves for pan/crop to keep focus centered during speech; emit automation tracks consumable by timeline/render.
- Production bar: deterministic automation outputs; tests assert focus windows align with semantic events.

## P9 – Batch Render & Preset Orchestration (many outputs, zero chaos)
- Implementation: create batch_render engine accepting project + render profiles + preset bundles (colour/text/crops); plan multiple render artifacts with isolated cache keys; ensure no shared mutable state; support dry-run scheduling; profile-level caching.
- Production bar: batch scheduling + plan generation tested; caching per-profile verified.

## P10 – Timeline Health & Complexity Analyzer (doctor)
- Implementation: timeline_analyzer engine computing track/effect counts, overlap density, audio loudness variance, approximate filter cost; outputs health score + hints (data-only); hook into render preflight as optional check.
- Production bar: fast, deterministic analyses with regression tests on synthetic complex timelines.

## P11 – Media Integrity & Colour Space Analyzer (preflight)
- Implementation: media integrity checks (truncated files, bad headers, inconsistent fps/sample rates); colour space analyzer (detect flags/metadata, flag mismatches/missing transforms); emit preflight report per asset before heavy work.
- Production bar: reproducible detections on crafted assets; integrates with media_v2 artifacts/meta; tests cover error cases.

## P12 – Low-Latency Preview Engine (scrub-friendly)
- Implementation: multi-resolution preview cache generator/manager; smart seek (pre-buffer/step playback) with fast preview path separate from final render; quality modes (draft/normal/high) toggle; timeline hooks to select preview sources.
- Production bar: smooth scrubbing on sample projects; preview path deterministic and covered by tests.

## P13 – Distributed Render Coordinator (local farm)
- Implementation: coordinator + worker model (local process or LAN) with registration/heartbeats; shard chunked renders across workers; progress/retry tracking; result aggregation and stitch trigger; deterministic scheduling for reproducible runs.
- Production bar: multi-worker integration tests on laptop/LAN; stitched outputs match single-machine render.

## P14 – Motif & Sequence Reuse Engine (pattern leverage)
- Implementation: motif definition (abstract sequence fragments with relative timing/effects); motif extraction from sequences; motif apply to new assets in other projects; ensure relative timing scales cleanly.
- Production bar: motif extract/apply deterministic; tests verify timing/effect preservation with new assets.

## P15 – Sequence History & Diff Engine (time travel)
- Implementation: timeline snapshotting at checkpoints; diff engine for clips/effects/transitions changes; structured changelog objects (data-only, no LLM); optional integration with render plans for audit trails.
- Production bar: diffs stable and fast; regression fixtures for add/remove/move/effect changes.
