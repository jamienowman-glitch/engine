# Engine Muscle Recon (MUSCLE-only, read-only pass)

## A. Summary by Domain

### 3D – Avatar / Scene / Animation
- Current Muscle: `scene_engine` maps box/grid recipes to SceneV2 graphs with cameras/environments/constraints plus export/import helpers; rich unit coverage across builders, camera shots, constraints, avatar styling/poses/kits. `mesh_kernel` offers primitive generation, Catmull-Clark subdivision, and sculpt stubs; `material_kernel` presets + region painting on meshes; `stage_kernel` spawns props/lights into SceneV2; `solid_kernel` sketches CAD-like ops (extrude/fillet/boolean history only); `animation_kernel` auto-rig + IK/walk-cycle mocks.
- Readiness Level: P2 (prod-lite) for `scene_engine` and geometry kernels (math covered in tests but no persistence/auth/export-hardening); P1 for `animation_kernel` and `solid_kernel` (toy kernels with stub math and no real rigging/CAD backend). No CAD ingest/BoQ engines present (P0 gap).

### 3D – CAD / BoQ / Plan-of-Works
- Current Muscle: None of the CAD/BoQ/plan-of-work engines from Lane B exist yet under `engines/*`.
- Readiness Level: P0 (missing).

### Video Stack
- Current Muscle: `media_v2` typed asset/artifact registry with S3/local storage adapters; `video_timeline` CRUD for projects/sequences/tracks/clips/filters/automation (HTTP); `video_render` builds ffmpeg graphs (filters/transitions/masks/regions/slowmo/stabilise/captions/voice-enhance) with chunk/job support; `video_mask` registers masks via stub backend; `video_regions`/`video_visual_meta` emit stubbed detections/visual-meta artifacts with HTTP routes; `video_multicam` builds aligned multi-track sequences + auto-cut; `video_presets`/`video_text` supply filter/motion presets and stylized text overlays; `video_captions` stub ASR + SRT converter; `video_360` projection metadata/transforms; `video_assist`, `video_focus_automation`, `video_motifs`, `video_history`, `video_edit_templates`, `video_preview`, `video_batch_render` scaffold edit assist/history/preview flows; `video_anonymise` wraps regions → blur filters; `video_stabilise` ffmpeg-based; `video_slowmo` optical-flow filter helper.
- Readiness Level: P3 for `video_render` and `video_timeline` (broad tests, real ffmpeg plans); P2 for `media_v2`, `video_multicam`, presets/text/360/captions/mask/regions/visual_meta/stabilise (HTTP + tests but stub detectors/backends and local storage fallbacks); P1 for assist/focus/motifs/history/edit_templates/preview/batch_render/anonymise (logic mostly heuristic/mock, minimal persistence or real detectors).

### Audio / Music / Beat Maker
- Current Muscle: HTTP `audio_service` orchestrates pipelines; `audio_semantic_timeline` caches stub semantic/beat timelines; `audio_voice_enhance` ffmpeg-chain enhancer with caching; `audio_sample_library` CRUD/tag queries; library engines `audio_hits`/`audio_loops`/`audio_voice_phrases` detect slices (librosa fallback); `audio_field_to_samples` orchestrates hits/loops/phrases; DSP utilities `audio_normalise`, `audio_resample`, `audio_fx_chain`, `audio_macro_engine`, `audio_separation` (demucs wrapper), `audio_groove`, `audio_performance_capture`, `audio_pattern_engine`, `audio_arrangement_engine`, `audio_structure_engine`, `audio_timeline`, `audio_mix_buses`, `audio_render` (ffmpeg mixer), `audio_to_video_origin`; CLI/backbone `audio_core` and `engines/audio/*` runners remain local-only.
- Readiness Level: P3- for `audio_service`, `audio_voice_enhance`, `audio_semantic_timeline`, `audio_field_to_samples`, `audio_render` (deterministic tests, ffmpeg-heavy but backends stubbed); P2 for hits/loops/phrases/library/normalise/resample/fx/macro/groove/pattern/arrangement/structure/mix_buses/performance_capture/to_video_origin (working math + tests, no HTTP + limited error handling); P1 for `audio_separation` (demucs dependency, minimal tests), `audio_core` + CLI ingest/ASR/beat_features (prototype scripts, no HTTP/persistence).

### Image / Photo Editing
- Current Muscle: `image_core` Pillow-based layer engine (colors/assets/text/vector layers, transforms, basic adjustments, blend modes, selections→mask rasterization) with artifact writes via media_v2; tests cover composite + masks.
- Readiness Level: P2 (prototype; local file assumptions, limited filters, no HTTP surface or performance/path safety).

### 2D Vector / Typography
- Current Muscle: `typography_core` renders text with font registry + basic wrapping/variation hooks; `vector_core` renders simple scenegraph (groups/rects/circles/paths) to raster for image_core; docs include FONTS_HELPER. Tests exist for both.
- Readiness Level: P2- (basic rendering only; lacks SVG I/O, layout metrics, boolean/path ops, variable-font axis control beyond size).

### Other Muscle (deterministic helpers)
- `video_slowmo` optical-flow filter helper and `video_stabilise` ffmpeg detector/apply; `audio_to_video_origin` produces shot lists from audio timelines. These are auxiliary and inherit readiness of their parent domains (mostly P2).

## B. Target App Fit (what works now vs missing)

- 3D Avatar Builder: Can prototype box/grid-based scene builds, camera/environment presets, simple materials/prop spawn, mock auto-rig + IK. Missing robust morph targets, parametric avatar sliders/kits, motion library/retargeting, export-quality USD/GLTF, persistence/versioning, real rendering.
- CAD ingest + costing + plan-of-works: No CAD ingest/BoQ/cost/plan engines exist; only solid_kernel stubs. Entire lane is a gap.
- Video Editor (CapCut-style): Usable backbone with media_v2 + timeline + render (filters/masks/regions/voice-enhance/captions, chunk jobs) and multicam auto-cut. Missing real detectors for regions/visual_meta/anonymise, GPU/proxy hardening, stable alignment, preview/assist maturity, robust storage for artifacts, better auth/error handling.
- Music / Beat-maker from field recordings: Field-to-samples + hits/loops/phrases work locally; semantic timeline + voice enhance + audio render/mix are present. Missing strong ASR/beat quality, HTTP for many engines, robust separation, richer FX/macro catalogs, DAW-grade automation/bus/stem workflows, persistence for patterns/arrangements.
- Photoshop-adjacent photo editor: Image_core supports basic layers/masks/adjustments/text/vector overlays. Missing full layer graph editing (blurs/curves/levels), selection tools variety, nondestructive history, GPU performance, HTTP/UI hooks.
- Illustrator-adjacent vector tool with variable fonts: Vector_core draws primitive paths; typography_core handles basic layout. Missing path boolean ops, guides/grids, variable font axis control, kerning/line-breaking fidelity, SVG import/export, text-on-path, interactions with image/video timelines.

## C. Gap List (Muscle only)

- 3D Avatar/Scene: No morph target pipeline, retargeting quality, animation library, persistence/export flows; rig/IK are mock-only; stage/material/mesh lack HTTP/persistence; solid_kernel not backed by real CAD kernel.
- 3D CAD: Entire ingest → semantics → BoQ → cost → plan-of-works stack absent.
- Video: Real detectors/captions/anon missing (stub backends); proxy/GPU/pushdown not hardened; preview/batch/assist/motifs/history mostly scaffolds; anonymise depends on stub regions; storage relies on local tmp if S3/GCS missing; auth/tenant scoping light in routes; focus/assist random heuristics.
- Audio: Many engines library-only (no HTTP); dependency fragility (ffmpeg/librosa/demucs); ASR/semantic backends stubbed; separation/groove/performance capture quality unproven; resample/fx/macro lack persistence/metadata consistency; no robust mix automation/bus editing UI layer; CLI pipelines ignore tenant/media_v2.
- Image: Limited filters/adjustments, no selection tools beyond simple masks, no history or project artifacts, assumes local asset paths.
- Vector/Type: No SVG I/O, boolean/path ops, layout precision/kerning control, variable-font axes beyond size, no artifact registration or HTTP surface.

## D. Recommended “Final Muscle” Phases (toward P3 for target apps)

- 3D Avatar / Scene
  - Phase 1: Rig/morph correctness — add tested morph targets, retargeting checks, FK/IK blend with real math, exportable skeleton data.
  - Phase 2: Parametric builder — sliders/presets/kits with persistence + versioned scene/asset storage; mesh/material/stage kernels exposed via HTTP.
  - Phase 3: Animation/export — motion library ingestion, clip remix tools, USD/GLTF export with materials/cameras/lights validated; perf/stability tests on larger scenes.
  - Phase 4: Lighting/render prep — stage/material QA, turntable renders or handoff specs for downstream renderer.
- 3D CAD
  - Phase 1: CAD ingest P0–P2 — parsers for common formats, topology healing, unit normalization, tests with fixtures.
  - Phase 2: Semantics/graph — element classification, layer → spatial graph, sectioning queries with deterministic tests.
  - Phase 3: BoQ/Cost — quantity extraction, unit conversions, rate libraries, currency/versioning, regression tests on sample plans.
  - Phase 4: Plan-of-works/diffs — task graph generation, sequencing, version diffs with impact reports; risk/compliance hooks later.
- Video
  - Phase 1: Real detectors — wire production backends for regions/visual_meta/anonymise/captions with artifact lineage + failure handling; tighten media_v2 storage (S3/GCS mandatory in prod).
  - Phase 2: Render/preview hardening — proxy generation, GPU profiles, retryable jobs, deterministic chunk stitching, better error surfacing; stabilize multicam alignment.
  - Phase 3: Assist/automation — deterministically scored highlights/focus/motifs/history with cached artifacts; anonymise enforcement in render; improve templates/presets coverage.
  - Phase 4: Broadcast polish — captions/subtitles export, color management/profile presets, batch render orchestration with idempotency and tenant scoping tests.
- Audio
  - Phase 1: Backend robustness — enforce ffmpeg/librosa/demucs availability, better error paths; expose hits/loops/phrases/normalise/resample/fx/macro via HTTP with media_v2 artifacts.
  - Phase 2: Semantic/ASR upgrade — real ASR/VAD/beat models with caching; quality metrics; stronger separation + groove extraction tests.
  - Phase 3: Creative timeline/mix — bus/automation editing, pattern/arrangement persistence, mix render stems with artifact lineage + loudness targets; performance capture quantise QA.
  - Phase 4: Library + origin — enrich sample library metadata/search, idempotent field_to_samples pipelines, audio_to_video_origin lineage in render/timeline flows.
- Image
  - Phase 1: Layer core hardening — full blend mode set, common adjustments (curves/levels/blur), mask editing, artifact persistence; HTTP surface.
  - Phase 2: Selections/masks — polygon/lasso/feather tools, mask artifacts reusable across video/image; performance tests on large canvases.
  - Phase 3: Interop/presets — export profiles, media_v2 artifact kinds for renders/masks, presets for looks and adjustments.
- Vector / Typography
  - Phase 1: Layout fidelity — kerning/line-breaking tests, variable font axis support, text-on-path; register rendered artifacts.
  - Phase 2: Vector ops — path boolean operations, transforms, SVG import/export round-trips, stroke/fill gradients.
  - Phase 3: Integration — expose HTTP services, tie vector/text layers into image_core/video_text presets with caching and tenant-scoped assets.
