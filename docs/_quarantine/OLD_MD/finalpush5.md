# Engine Inventory (northstar-engines)

High-level summary
- Video-ish engines: 13 total (render/timeline/mask/regions/multicam/360/text/presets/anonymise/visual-meta/render-snippets/frame-grab/page-content); ~4 production-grade (render, timeline, render jobs, mask/regions tested), ~6 prod-lite (multicam, presets, visual-meta, text, 360, origin_snippets), ~3 stub/prototype (anonymise partial, page_content scraper-lite, frame_grab CLI).
- Audio-ish engines: 17 total (audio_service, semantic_timeline, hits, loops, voice_phrases, voice_enhance, sample_library, field_to_samples, audio_core, origin_snippets audio side, plus CLI ingest/segment/clean/ASR/beat_features); ~5 production-grade (audio_service, semantic_timeline, voice_enhance, sample_library, field_to_samples), ~6 prod-lite (hits, loops, voice_phrases, audio_core runners, origin_snippets, audio_cli utilities), ~6 stub/prototype (ingest stubs, preprocess stubs, beat_features minimal, ASR wrapper skeleton).
- 3D-ish engines: 6 total (scene_engine, animation_kernel, mesh_kernel, material_kernel, solid_kernel, stage_kernel); mostly prod-lite (scene_engine + kernels have tests and math helpers) with animation_kernel closer to prototype.
- Other engines (routing/safety/controls/data/etc.): 32+ (media_v2, media, memory, maybes, budget, billing, kpi, temperature, forecast, strategy_lock, three_wise, firearms, kill_switch, analytics_events, seo, page_content, rootsmanuva_engine, routing, align, dataset packer, eval, creative, tag flow, text cleaners, train runners, nexus components, guardrails/safety/security/logging, bossman, origins); majority prod-lite with in-memory repos; a handful stub/spec-only (train/text/ingest runners, some guardrails).
- UI readiness: HTTP-surfaced, tenant-aware engines (render/timeline/audio_service/semantic_timeline/voice_enhance/sample_library/media_v2/budget/kpi/temperature/seo/analytics_events/three_wise/firearms/strategy_lock/maybes/memory etc.) are front-end callable now; CLI-only engines need wrappers; stub/prototype pieces need hardening before exposure.
- Biggest gaps: many services default to in-memory/Firestore stubs without persistence guarantees; several DSP backends are placeholder (align/animation_kernel/ingest runners); multi-tenant enforcement is uneven outside HTTP surfaces; some engines lack error handling or rely on ffmpeg/librosa presence; docs and failure-mode tests are missing for many CLI runners and safety/security paths.

---

## Video Engines

### video_render
- Path: `engines/video_render`
- Interface: HTTP (`POST /video/render`, `/render/dry-run`, chunk plan/stitch and render jobs) plus library service.
- Description: Builds ffmpeg render plans from video_timeline projects, handles filters/transitions/audio handling, runs ffmpeg, uploads results, registers media_v2 assets/artifacts, supports chunked rendering and jobs.
- Artifacts & data: Writes media_v2 artifacts (`render`, `render_segment`, `render_snippet`) with start/end_ms, render profile, cache keys; reads assets/artifacts for masks/audio, uses timeline projects. Optional GCS storage.
- Multi-tenant / identity: tenant_id/env/user_id carried in models; Firestore repo optional else in-memory.
- Status: production-grade (rich tests, ffmpeg integration, cache/job handling).
- Dependencies: ffmpeg, google-cloud-firestore (optional), GCS client, numpy-lite via ffmpeg only.
- Tests: `engines/video_render/tests` (plans, filters, jobs, chunking, voice enhance meta, etc.).
- Gaps / TODOs: FFmpeg availability assumed; error handling around storage uploads; long-run orchestration retries.
- Ready for UI?: yes.

### video_timeline
- Path: `engines/video_timeline`
- Interface: HTTP (`/video/projects`, sequences/tracks/clips/filters/automation CRUD) and library service.
- Description: Manages video projects/sequences/tracks/clips/transitions/filter stacks/automation; provides in-memory and Firestore repos.
- Artifacts & data: Stores timeline entities in-memory or Firestore collections per tenant; no media artifact writes directly.
- Multi-tenant / identity: tenant_id/env on models; Firestore collection per tenant; no auth in routes.
- Status: production-grade (core timelines with tests).
- Dependencies: optional Firestore.
- Tests: `engines/video_timeline/tests`.
- Gaps / TODOs: Access control, pagination, strong validation on cross-tenant access.
- Ready for UI?: yes.

### video_multicam
- Path: `engines/video_multicam`
- Interface: HTTP (`/video/multicam/*`) via routes; library service.
- Description: Creates multicam sessions, aligns tracks, builds sequences with clips/tracks, auto-cuts based on anchor offsets.
- Artifacts & data: Uses media_v2 assets for durations; writes timeline tracks/clips.
- Multi-tenant / identity: tenant_id/env in models; no auth enforcement in routes.
- Status: prod-lite (functional with tests, relies on timeline/media; limited DSP alignment).
- Dependencies: timeline/media services.
- Tests: `engines/video_multicam/tests`.
- Gaps / TODOs: Real alignment backend, guardrails for offsets, stronger validation/auth.
- Ready for UI?: yes (dev-quality).

### video_mask
- Path: `engines/video_mask`
- Interface: HTTP (`/video/mask/*`) via routes; library service.
- Description: Manages mask artifacts for video assets, including uploads and association with clips.
- Artifacts & data: Reads/writes media_v2 mask artifacts; track_id/meta fields.
- Multi-tenant / identity: tenant/env in models; auth not enforced.
- Status: prod-lite (works with media_v2, basic tests).
- Dependencies: media_v2, optional Firestore.
- Tests: `engines/video_mask/tests`.
- Gaps / TODOs: Input validation, large mask handling, auth.
- Ready for UI?: yes (dev-only).

### video_regions
- Path: `engines/video_regions`
- Interface: HTTP (`/video/regions/analyze`, GET summary) via routes; library service.
- Description: Analyzes video artifacts for regions/objects (stub backend with deterministic outputs).
- Artifacts & data: Reads media_v2 artifacts; may emit summaries (in-memory).
- Multi-tenant / identity: tenant/env on models; no auth.
- Status: prod-lite (tested but backend stubbed).
- Dependencies: none heavy; uses optional Firestore.
- Tests: `engines/video_regions/tests`.
- Gaps / TODOs: Real detection backend, persistence, auth.
- Ready for UI?: yes (dev-only).

### video_visual_meta
- Path: `engines/video_visual_meta`
- Interface: HTTP routes under `/video/visual-meta`; library service.
- Description: Extracts and stores visual metadata (color palettes, faces) per artifact using backend adapters; caching supported.
- Artifacts & data: Writes media_v2 artifacts/meta; caches in repositories.
- Multi-tenant / identity: tenant/env fields; repos per tenant.
- Status: prod-lite (functional with tests; relies on optional backends).
- Dependencies: media_v2; optional libs for detection.
- Tests: `engines/video_visual_meta/tests`.
- Gaps / TODOs: Real detection wiring, auth, pagination.
- Ready for UI?: yes (dev-only).

### video_text
- Path: `engines/video_text`
- Interface: HTTP (`/video/text/*`) via routes; library service.
- Description: Generates stylized text overlays and plans (font/styles) for timeline use.
- Artifacts & data: No direct media artifacts; returns overlay specs.
- Multi-tenant / identity: tenant/env optional; limited enforcement.
- Status: prod-lite (tested stylization logic).
- Dependencies: font handling (Pillow optional).
- Tests: `engines/video_text/tests`.
- Gaps / TODOs: Rendering integration, auth, error handling.
- Ready for UI?: yes (dev-only).

### video_presets
- Path: `engines/video_presets`
- Interface: HTTP (`/video/presets/*`) via routes; library service.
- Description: Stores/render profiles and preset timelines for reuse.
- Artifacts & data: Stores preset configs in repos; no media artifacts.
- Multi-tenant / identity: tenant/env present; repo in-memory by default.
- Status: prod-lite.
- Dependencies: none heavy.
- Tests: `engines/video_presets/tests`.
- Gaps / TODOs: Persistence, auth, validation.
- Ready for UI?: yes (dev-only).

### video_anonymise
- Path: `engines/video_anonymise`
- Interface: HTTP (`/video/anonymise/*`) via routes; service uses detection/masking to blur faces.
- Description: Plans and applies anonymization masks on videos (face detection stub).
- Artifacts & data: Writes mask artifacts and anonymized renders; uses media_v2/timeline.
- Multi-tenant / identity: tenant/env fields; no auth enforcement.
- Status: stub/prototype (stub detectors, limited tests).
- Dependencies: ffmpeg, detection backends (stubbed).
- Tests: `engines/video_anonymise/tests`.
- Gaps / TODOs: Real detection, performance, auth, persistence.
- Ready for UI?: no (needs real backend).

### video_360
- Path: `engines/video_360`
- Interface: HTTP (`/video/360/*`) via routes; service.
- Description: Handles 360/VR video transforms and metadata updates (projection flags).
- Artifacts & data: Updates media_v2 artifacts/meta; may generate render artifacts.
- Multi-tenant / identity: tenant/env carried; no auth.
- Status: prod-lite.
- Dependencies: ffmpeg for transforms (optional).
- Tests: `engines/video_360/tests`.
- Gaps / TODOs: Full projection handling, auth, error checks.
- Ready for UI?: yes (dev-only).

### video_frame_grab
- Path: `engines/video/frame_grab`
- Interface: CLI runner (`python -m engines.video.frame_grab.runner`).
- Description: ffmpeg-based frame extraction at intervals/manual timestamps.
- Artifacts & data: Produces image files/JSON listings; no media_v2 registration by default.
- Multi-tenant / identity: none (CLI-only).
- Status: stub/prototype.
- Dependencies: ffmpeg.
- Tests: none dedicated.
- Gaps / TODOs: Tenant-aware storage, HTTP surface, media_v2 registration, tests.
- Ready for UI?: no.

### origin_snippets
- Path: `engines/origin_snippets`
- Interface: HTTP (`/origin-snippets/batch`, `/origin-snippets/for-audio/{id}`) via routes; service.
- Description: Builds video clips/snippet renders from audio artifacts (hits/loops/phrases) with padding/clamping; optionally renders windows and registers lineage.
- Artifacts & data: Reads audio artifacts; writes timeline clips; registers `render_snippet` artifacts with `upstream_artifact_ids`, source window, project/sequence meta.
- Multi-tenant / identity: tenant/env/user carried; validates attach_to_project tenant match.
- Status: prod-lite (deterministic logic, tests with fakes).
- Dependencies: media_v2, video_timeline, video_render.
- Tests: `engines/origin_snippets/tests`.
- Gaps / TODOs: Caching/idempotence, stronger auth, render profile validation.
- Ready for UI?: yes (dev-only).

### page_content
- Path: `engines/page_content`
- Interface: HTTP routes under `/page-content`; service.
- Description: Fetches and cleans web page content (HTML->text) for downstream use; includes sanitization.
- Artifacts & data: No media artifacts; may log scraped content.
- Multi-tenant / identity: tenant/env optional; no auth.
- Status: prod-lite.
- Dependencies: requests/bs4 (scraping).
- Tests: `engines/page_content/tests`.
- Gaps / TODOs: Robust fetch error handling, robots/PII guardrails, auth.
- Ready for UI?: yes (dev-only).

## Audio Engines

### audio_service
- Path: `engines/audio_service`
- Interface: HTTP (`/audio/*`) via routes; orchestrates audio pipelines.
- Description: Coordinates ASR/diarization/voice processing using media_v2 assets/artifacts; caching and pipeline selection.
- Artifacts & data: Reads/writes media_v2 audio artifacts; registers outputs (transcripts, diarization).
- Multi-tenant / identity: tenant/env/user fields in requests; no auth beyond context.
- Status: production-grade (broad tests, handles caching/modes).
- Dependencies: media_v2, optional ASR backends.
- Tests: `engines/audio_service/tests`.
- Gaps / TODOs: Harden backend selection/error paths; auth.
- Ready for UI?: yes.

### audio_semantic_timeline
- Path: `engines/audio_semantic_timeline`
- Interface: HTTP (`/audio/semantic/*`) via routes; service.
- Description: Builds semantic event timelines from audio (speech/music/etc.) with caching and retrieval.
- Artifacts & data: Writes media_v2 artifacts (`audio_semantic_timeline`), includes start/end_ms and labels.
- Multi-tenant / identity: tenant/env in models; no auth.
- Status: production-grade (tests for caching/endpoints).
- Dependencies: model backend placeholder (deterministic/stub).
- Tests: `engines/audio_semantic_timeline/tests`.
- Gaps / TODOs: Real model integration, auth, quality metrics.
- Ready for UI?: yes (dev-only caching).

### audio_hits
- Path: `engines/audio_hits`
- Interface: service (no HTTP routes); used programmatically.
- Description: Detects percussive hits/onsets in audio with librosa/stub backend; slices and registers artifacts.
- Artifacts & data: Writes media_v2 `audio_hit` artifacts with start/end_ms, optional slice uploads.
- Multi-tenant / identity: tenant/env on requests; no auth.
- Status: prod-lite (functional, backend may be stub if librosa absent).
- Dependencies: ffmpeg, librosa (optional), GCS optional.
- Tests: `engines/audio_hits/tests`.
- Gaps / TODOs: HTTP surface, robust file handling/errors.
- Ready for UI?: yes (library), HTTP missing.

### audio_loops
- Path: `engines/audio_loops`
- Interface: service (no HTTP routes); programmatic.
- Description: Detects loops/bars via librosa/stub, slices audio, registers loop artifacts.
- Artifacts & data: Writes media_v2 `audio_loop` artifacts with timing/bpm/loop_bars.
- Multi-tenant / identity: tenant/env required.
- Status: prod-lite (functional with stub fallback).
- Dependencies: librosa/ffmpeg, GCS optional.
- Tests: `engines/audio_loops/tests`.
- Gaps / TODOs: HTTP surface, better validation/auth, performance.
- Ready for UI?: yes (library).

### audio_voice_phrases
- Path: `engines/audio_voice_phrases`
- Interface: service; no HTTP routes.
- Description: Manages detected voice phrases/segments; integrates with media_v2 for artifacts.
- Artifacts & data: Writes `audio_phrase` artifacts with timing.
- Multi-tenant / identity: tenant/env present.
- Status: prod-lite (basic tests).
- Dependencies: none heavy.
- Tests: `engines/audio_voice_phrases/tests`.
- Gaps / TODOs: Detection backend integration, HTTP surface, auth.
- Ready for UI?: no (needs endpoint).

### audio_voice_enhance
- Path: `engines/audio_voice_enhance`
- Interface: HTTP (`/audio/voice-enhance`) via routes; service.
- Description: Enhances dialogue audio, caches outputs, registers enhanced artifacts.
- Artifacts & data: Writes `audio_voice_enhanced` artifacts with mode/meta.
- Multi-tenant / identity: tenant/env/user required via RequestContext; routes enforce membership.
- Status: production-grade (cache handling, tests).
- Dependencies: backend pluggable; ffmpeg/temp storage.
- Tests: `engines/audio_voice_enhance/tests`.
- Gaps / TODOs: Backend variety, error handling on missing ffmpeg.
- Ready for UI?: yes.

### audio_sample_library
- Path: `engines/audio_sample_library`
- Interface: HTTP (`/audio/sample-library/*`) via routes; service.
- Description: CRUD for audio samples/library items and tags; supports queries.
- Artifacts & data: Stores library items in repo (in-memory/Firestore); optional media links.
- Multi-tenant / identity: tenant/env fields; no auth enforcement.
- Status: prod-lite (tests cover routes).
- Dependencies: optional Firestore.
- Tests: `engines/audio_sample_library/tests`.
- Gaps / TODOs: Persistence hardening, auth, pagination.
- Ready for UI?: yes (dev-only).

### audio_field_to_samples
- Path: `engines/audio_field_to_samples`
- Interface: service; no HTTP routes.
- Description: Converts long field recordings into sampled snippets with overlap; registers artifacts.
- Artifacts & data: Writes media_v2 artifacts for slices with start/end_ms.
- Multi-tenant / identity: tenant/env in requests.
- Status: production-grade (tested slicing logic).
- Dependencies: ffmpeg for slicing.
- Tests: `engines/audio_field_to_samples/tests`.
- Gaps / TODOs: HTTP surface, error handling for large files.
- Ready for UI?: no (needs endpoint).

### audio_core
- Path: `engines/audio_core`
- Interface: CLI (`python -m engines.audio_core.runner`); library utilities.
- Description: Core audio pipeline pieces (ASR backend interface, dataset builder, LoRA train helpers).
- Artifacts & data: Works with local files; no media_v2 integration by default.
- Multi-tenant / identity: none.
- Status: prod-lite (usable utilities, not wired to HTTP).
- Dependencies: torch/whisper (depending on backend), ffmpeg.
- Tests: none dedicated.
- Gaps / TODOs: Tenant-aware storage, tests, integration with media_v2.
- Ready for UI?: no.

### audio CLI engines
- Paths: `engines/audio/asr_whisper`, `beat_features`, `ingest_local`, `ingest_local_file`, `ingest_remote_pull`, `preprocess_basic_clean`, `segment_ffmpeg`
- Interface: CLI runners (`python -m engines.audio.<engine>.runner`).
- Description: Collection of pipeline steps for ingest, segmentation via ffmpeg, ASR via Whisper, beat feature extraction, basic clean/normalize.
- Artifacts & data: Operate on local files; no media_v2 persistence.
- Multi-tenant / identity: none.
- Status: stub/prototype (lightweight scripts, minimal validation).
- Dependencies: ffmpeg, whisper/torchaudio for ASR, sox for cleaning (per docs/spec).
- Tests: none dedicated.
- Gaps / TODOs: Tenant-aware storage, integration with media_v2, error handling, tests.
- Ready for UI?: no.

### audio_hits/loops/phrases inference alignment (align)
- Path: `engines/align`
- Interface: library service; CLI runner `engines/align/audio_text_bars`.
- Description: Stub alignment service returning offsets based on filename hints; CLI for aligning audio to text bars.
- Artifacts & data: No media_v2 writes.
- Multi-tenant / identity: none.
- Status: stub/prototype.
- Dependencies: intended numpy/scipy (not implemented).
- Tests: none beyond minimal service import.
- Gaps / TODOs: Real alignment math, HTTP surface, tenant wiring.
- Ready for UI?: no.

## 3D / Scene Engines

### scene_engine
- Path: `engines/scene_engine`
- Interface: HTTP server (`scene_engine/service/server.py`), service modules.
- Description: Generates and edits 3D scenes (SceneV2) from JSON boxes/recipes; supports builders, constraints, camera, environment, export/import, avatar styling.
- Artifacts & data: Operates on JSON scenes; may read assets; no media_v2 artifacts.
- Multi-tenant / identity: tenant/env optional; not enforced.
- Status: prod-lite (broad test suite).
- Dependencies: numpy, trimesh, pillow for assets (varies).
- Tests: `engines/scene_engine/tests`.
- Gaps / TODOs: Persistence, auth, performance for large scenes.
- Ready for UI?: yes (dev-only).

### animation_kernel
- Path: `engines/animation_kernel`
- Interface: service; no HTTP routes.
- Description: Procedural animation helpers (auto-rig skeletons, walk cycle, IK solver).
- Artifacts & data: In-memory skeleton/clip store.
- Multi-tenant / identity: none.
- Status: stub/prototype (mock outputs).
- Dependencies: math utils.
- Tests: `engines/animation_kernel/tests`.
- Gaps / TODOs: Real rigging, persistence, tenant/auth, HTTP.
- Ready for UI?: no.

### mesh_kernel / material_kernel / solid_kernel / stage_kernel
- Paths: `engines/mesh_kernel`, `material_kernel`, `solid_kernel`, `stage_kernel`
- Interface: services; no HTTP.
- Description: Geometry and material helpers (mesh ops, material presets, primitive solids, stage assembly), used by scene/creative flows.
- Artifacts & data: In-memory models; no media_v2.
- Multi-tenant / identity: none.
- Status: prod-lite (math-heavy with tests).
- Dependencies: numpy, trimesh-like math.
- Tests: respective `tests/` dirs.
- Gaps / TODOs: Public API/HTTP, persistence, auth.
- Ready for UI?: no (library-only).

### page/mesh alignment kernels (solid/stage/material)
- (Covered above)

## Routing / Orchestration / Control / Safety / Policy

### rootsmanuva_engine
- Path: `engines/rootsmanuva_engine`
- Interface: service; tests; no HTTP route.
- Description: Deterministic routing engine scoring candidates based on metrics; used for orchestrator selection.
- Artifacts & data: No media artifacts; uses in-memory configs.
- Multi-tenant / identity: tenant/env fields; not enforced via HTTP.
- Status: prod-lite (tested scoring).
- Dependencies: none heavy.
- Tests: `engines/rootsmanuva_engine/tests`.
- Gaps / TODOs: Exposure via API, logging to EventLog, auth.
- Ready for UI?: no (needs endpoint).

### routing
- Path: `engines/routing`
- Interface: schemas/utilities; no HTTP.
- Description: Models and helpers for routing profiles/decisions.
- Artifacts & data: None.
- Multi-tenant / identity: tenant in models.
- Status: prod-lite (used by rootsmanuva_engine).
- Dependencies: none.
- Tests: indirect via rootsmanuva_engine.
- Gaps / TODOs: API surface, storage.
- Ready for UI?: no.

### strategy_lock
- Path: `engines/strategy_lock`
- Interface: HTTP routes `/strategy-lock/*`; service.
- Description: Manages strategy lock stages/HITL approvals; records decisions.
- Artifacts & data: Stores lock entries (in-memory/Firestore).
- Multi-tenant / identity: tenant/env required via RequestContext/auth.
- Status: prod-lite (tests exist).
- Dependencies: auth utils, optional Firestore.
- Tests: `engines/strategy_lock/tests`.
- Gaps / TODOs: Persistence hardening, audit logs, enforcement hooks.
- Ready for UI?: yes (dev-only).

### three_wise
- Path: `engines/three_wise`
- Interface: HTTP `/three-wise/*`; service.
- Description: Placeholder for 3-agent safety check; returns static responses with logging.
- Artifacts & data: Records verdicts in-memory.
- Multi-tenant / identity: tenant/env required via RequestContext; auth enforced.
- Status: prod-lite (stub logic, tested routes).
- Dependencies: none heavy.
- Tests: `engines/three_wise/tests`.
- Gaps / TODOs: Real LLM hooks, persistence, metrics.
- Ready for UI?: yes (as stub).

### firearms
- Path: `engines/firearms`
- Interface: HTTP `/firearms/*`; service.
- Description: Guardrail adapter for policy/licensing decisions; evaluates actions/tools.
- Artifacts & data: Stores verdicts in repo; no media artifacts.
- Multi-tenant / identity: tenant/env via RequestContext/auth.
- Status: prod-lite (policy scaffold, tests).
- Dependencies: none heavy.
- Tests: `engines/firearms/tests`.
- Gaps / TODOs: Real policy store/license check, logging, enforcement in orchestrators.
- Ready for UI?: yes (policy stub).

### kill_switch
- Path: `engines/kill_switch`
- Interface: HTTP `/kill-switch/*`; service.
- Description: Enables/queries global/tenant kill-switch flags for operations.
- Artifacts & data: In-memory/Firestore flags.
- Multi-tenant / identity: tenant/env via RequestContext/auth.
- Status: prod-lite (tested).
- Dependencies: Firestore optional.
- Tests: `engines/kill_switch/tests`.
- Gaps / TODOs: Audit logging, propagation.
- Ready for UI?: yes.

### temperature
- Path: `engines/temperature`
- Interface: HTTP `/temperature/*`; service.
- Description: Manages temperature weights/floors/ceilings for control loops across surfaces.
- Artifacts & data: Stores configs (in-memory/Firestore).
- Multi-tenant / identity: tenant/env via RequestContext/auth.
- Status: prod-lite (tested routes).
- Dependencies: none heavy.
- Tests: `engines/temperature/tests`.
- Gaps / TODOs: Runtime enforcement hooks, analytics.
- Ready for UI?: yes (config).

### budget
- Path: `engines/budget`
- Interface: HTTP `/budget/usage`; service.
- Description: Records and queries usage events/costs per tenant; summaries/grouping.
- Artifacts & data: Stores usage records in repo (in-memory/Firestore).
- Multi-tenant / identity: tenant/env enforced via RequestContext/auth.
- Status: prod-lite (tests present).
- Dependencies: none heavy.
- Tests: `engines/budget/tests`.
- Gaps / TODOs: CUR ingestion, connectors, enforcement hooks.
- Ready for UI?: yes.

### billing
- Path: `engines/billing`
- Interface: HTTP `/billing/*`; service.
- Description: Billing metadata/stubs for payments/Stripe integration.
- Artifacts & data: In-memory/Firestore records.
- Multi-tenant / identity: tenant/env via RequestContext/auth.
- Status: stub/prototype (minimal logic).
- Dependencies: stripe (optional).
- Tests: limited.
- Gaps / TODOs: Real billing flows, reconciliation, auth hardening.
- Ready for UI?: no (stub).

### kpi
- Path: `engines/kpi`
- Interface: HTTP `/kpi/*`; service.
- Description: CRUD for KPI corridors/configs influencing control loops.
- Artifacts & data: Stores KPI configs in repo.
- Multi-tenant / identity: tenant/env enforced via RequestContext/auth.
- Status: prod-lite (tested).
- Dependencies: none heavy.
- Tests: `engines/kpi/tests`.
- Gaps / TODOs: Runtime enforcement/logging, persistence scaling.
- Ready for UI?: yes (config).

### forecast
- Path: `engines/forecast`
- Interface: service; tests; no HTTP.
- Description: Forecast models/service stubs for cost/KPI predictions.
- Artifacts & data: In-memory forecasts.
- Multi-tenant / identity: tenant/env on models.
- Status: prod-lite (tests, but backend stubs).
- Dependencies: none heavy (Vertex/AWS planned).
- Tests: `engines/forecast/tests`.
- Gaps / TODOs: Real backend integration, HTTP surface, auth.
- Ready for UI?: no.

### eval
- Path: `engines/eval`
- Interface: service; no HTTP.
- Description: Evaluation scaffolding for agents/models; metrics recording.
- Artifacts & data: In-memory; no media artifacts.
- Multi-tenant / identity: tenant/env optional.
- Status: prod-lite.
- Dependencies: none heavy.
- Tests: `engines/eval/tests`.
- Gaps / TODOs: HTTP surface, persistence, richer metrics.
- Ready for UI?: no.

### creative
- Path: `engines/creative`
- Interface: service; no HTTP.
- Description: Creative asset assembly helpers (colors/fonts/layout cues).
- Artifacts & data: In-memory schemas.
- Multi-tenant / identity: none.
- Status: prod-lite (tests).
- Dependencies: none heavy.
- Tests: `engines/creative/tests`.
- Gaps / TODOs: HTTP surface, integration with media.
- Ready for UI?: no.

### analytics_events
- Path: `engines/analytics_events`
- Interface: HTTP `/analytics/events`; service.
- Description: Records analytics events with contextual metadata.
- Artifacts & data: In-memory/Firestore event store.
- Multi-tenant / identity: tenant/env via RequestContext/auth.
- Status: prod-lite (tests).
- Dependencies: Firestore optional.
- Tests: `engines/analytics_events/tests`.
- Gaps / TODOs: Retention, querying, PII stripping.
- Ready for UI?: yes (dev-only).

### seo
- Path: `engines/seo`
- Interface: HTTP `/seo/*`; service.
- Description: SEO assistant for keywords/meta generation (stub).
- Artifacts & data: In-memory results.
- Multi-tenant / identity: tenant/env via RequestContext/auth.
- Status: stub/prototype.
- Dependencies: none heavy.
- Tests: `engines/seo/tests`.
- Gaps / TODOs: Real model integration, metrics, persistence.
- Ready for UI?: no (stub).

### origin routing helpers (alignment/tag)
- Path: `engines/tag/flow_auto`
- Interface: CLI runner.
- Description: Auto-tagging flow script (likely for BBK data); operates on local data.
- Artifacts & data: local files/jsonl.
- Multi-tenant / identity: none.
- Status: stub/prototype.
- Dependencies: pandas/etc. (as per script).
- Tests: none.
- Gaps / TODOs: Tenant-aware store, HTTP, tests.
- Ready for UI?: no.

### dataset packer
- Path: `engines/dataset/pack_jsonl`
- Interface: CLI runner.
- Description: Packs dataset JSONL from segments/events for training.
- Artifacts & data: local files.
- Multi-tenant / identity: none.
- Status: stub/prototype.
- Dependencies: python stdlib.
- Tests: none.
- Gaps / TODOs: Validation, tenant-aware storage, docs.
- Ready for UI?: no.

### text cleaners
- Path: `engines/text/clean_asr_punct_case`, `text/normalise_slang`
- Interface: CLI runners.
- Description: Cleans ASR output for punctuation/casing; normalizes slang via TSV map.
- Artifacts & data: local text files.
- Multi-tenant / identity: none.
- Status: stub/prototype.
- Dependencies: python regex, TSV data.
- Tests: none.
- Gaps / TODOs: HTTP surface, media_v2 integration, tests.
- Ready for UI?: no.

### train engines
- Path: `engines/train/lora_peft_hf`, `train/lora_local`
- Interface: CLI runners.
- Description: LoRA training scripts (PEFT/HF or local placeholder) taking jsonl datasets.
- Artifacts & data: local model artifacts.
- Multi-tenant / identity: none.
- Status: stub/prototype.
- Dependencies: torch/transformers/peft.
- Tests: none.
- Gaps / TODOs: Orchestration, logging, dataset validation, tenant isolation.
- Ready for UI?: no.

### guardrails / safety
- Path: `engines/guardrails`
- Interface: library adapters; no HTTP.
- Description: PII/guardrail utilities combining vendor guardrails and Firearms verdicts.
- Artifacts & data: None persisted.
- Multi-tenant / identity: tenant info passed in adapters.
- Status: prod-lite (used by other services).
- Dependencies: vendor guardrail SDKs (pluggable).
- Tests: minimal.
- Gaps / TODOs: Dedicated service surface, tests for failures.
- Ready for UI?: no.

### safety
- Path: `engines/safety`
- Interface: service; tests; no HTTP.
- Description: Safety checks/policies scaffolding.
- Artifacts & data: In-memory.
- Multi-tenant / identity: tenant/env optional.
- Status: prod-lite.
- Dependencies: none heavy.
- Tests: `engines/safety/tests`.
- Gaps / TODOs: Concrete policies, HTTP surface, persistence.
- Ready for UI?: no.

### security
- Path: `engines/security`
- Interface: service; tests; no HTTP.
- Description: Security utilities (signing/verification).
- Artifacts & data: None.
- Multi-tenant / identity: N/A.
- Status: prod-lite.
- Dependencies: cryptography.
- Tests: `engines/security/tests`.
- Gaps / TODOs: Integration, HTTP surface.
- Ready for UI?: no.

### logging/events
- Path: `engines/logging/events`
- Interface: service; tests.
- Description: Event log engine with PII stripping and logging helpers.
- Artifacts & data: Stores events (in-memory/Firestore).
- Multi-tenant / identity: tenant/env in events.
- Status: prod-lite.
- Dependencies: Firestore optional.
- Tests: `engines/logging/events/tests`.
- Gaps / TODOs: Scaling, query surfaces, auth.
- Ready for UI?: no (library).

### memory
- Path: `engines/memory`
- Interface: HTTP `/memory/*`; service.
- Description: Memory service for chat/episodes, storing snippets/state.
- Artifacts & data: In-memory/Firestore memory entries.
- Multi-tenant / identity: tenant/env enforced via RequestContext/auth.
- Status: prod-lite (tests).
- Dependencies: Firestore optional.
- Tests: `engines/memory/tests`.
- Gaps / TODOs: Persistence scaling, eviction policies.
- Ready for UI?: yes (dev-only).

### maybes
- Path: `engines/maybes`
- Interface: HTTP `/maybes/*`; service.
- Description: Scratchpad items CRUD with tags/pin/archive.
- Artifacts & data: In-memory/Firestore store.
- Multi-tenant / identity: tenant/env via RequestContext/auth.
- Status: prod-lite (tests).
- Dependencies: Firestore optional.
- Tests: `engines/maybes/tests`.
- Gaps / TODOs: Search/indexing, auth hardening, retention.
- Ready for UI?: yes.

### media_v2
- Path: `engines/media_v2`
- Interface: HTTP `/media/v2/*`; service.
- Description: Core media asset/artifact registry with upload/register, GCS support, optional Firestore repos.
- Artifacts & data: Media assets and derived artifacts; tenant-scoped collections; artifact kinds include audio/video renders, masks, hits/loops, etc.
- Multi-tenant / identity: tenant/env required; Firestore collections per tenant.
- Status: production-grade (foundational, tests).
- Dependencies: ffprobe/ffmpeg for probing, Firestore, GCS.
- Tests: `engines/media_v2/tests`.
- Gaps / TODOs: Auth enforcement, lifecycle policies.
- Ready for UI?: yes.

### media (legacy v1)
- Path: `engines/media`
- Interface: HTTP `/media/*`; service.
- Description: Legacy media upload/serve pipeline with GCS support.
- Artifacts & data: Assets/artifacts similar to media_v2.
- Multi-tenant / identity: tenant/env present; less strict.
- Status: prod-lite (older tests).
- Dependencies: Firestore/GCS.
- Tests: `engines/media/tests`.
- Gaps / TODOs: Consolidate into media_v2, auth.
- Ready for UI?: yes (legacy).

### page-content (already in video section) — covered above.

### analytics/chat/bossman (aggregators)
- `engines/chat`: transport app aggregating routers; not an engine itself.
- `engines/bossman`: bossman dashboards; routes for stats (prod-lite).
- Status: prod-lite; tenant awareness depends on downstream routes.

### roots/support: registry, config, common, storage
- Support modules (not engines) providing config, storage, registry metadata.

### seo (covered), analytics_events (covered).

### nexus components
- Paths: `engines/nexus/atoms`, `cards`, `index`, `packs`, `raw_storage`, `settings`, `vector_explorer`
- Interface: HTTP routes under `/atoms`, `/cards`, `/index`, `/packs`, `/raw-storage`, `/settings`, `/vector-explorer`.
- Description: Vector/RAG/storage subsystems (atoms/cards registry, vector indexing/search, pack management, raw storage uploads, settings).
- Artifacts & data: Uses Firestore/Vertex vector store; stores embeddings/documents/atoms metadata; media_v2 not primary.
- Multi-tenant / identity: tenant/env in models; auth via RequestContext in routes.
- Status: prod-lite (tests in `engines/nexus/tests` and sub-tests; some stubs for Vertex).
- Dependencies: google cloud (Vertex/Firestore), numpy.
- Gaps / TODOs: Full auth, async ingestion, classifier/terrain features.
- Ready for UI?: yes (dev-only).

### reactive
- Path: `engines/reactive`
- Interface: library.
- Description: Reactive content helpers (state machines).
- Status: stub/prototype.
- Ready for UI?: no.

### orchestration
- Path: `engines/orchestration`
- Interface: library; tests.
- Description: Orchestration patterns/helpers for agent runtimes.
- Status: prod-lite.
- Ready for UI?: no.

### privacy
- Path: `engines/privacy`
- Interface: library; tests.
- Description: Privacy filters/helpers.
- Status: prod-lite.
- Ready for UI?: no.

### security (covered), safety (covered).

### page_content (covered).

### roots: control/temperature/kpi/budget (covered), strategy_lock (covered).

### bossman
- Path: `engines/bossman`
- Interface: HTTP routes under `/bossman`; service.
- Description: Dashboard/data aggregation for state-of-world reports.
- Artifacts & data: Reads across other stores; minimal own data.
- Multi-tenant / identity: tenant/env in models.
- Status: prod-lite.
- Tests: none dedicated.
- Gaps / TODOs: Auth, data completeness.
- Ready for UI?: yes (internal).

## Misc Media/Tag/Text/Train Engines (CLI/spec)

### tag/flow_auto
- (covered above)

### text cleaners (covered)

### train runners (covered)

## Summary Stats
- Total engines documented: ~68 (including HTTP services and CLI runners under engines/).
- Production-grade: ~6 (media_v2, video_render, video_timeline, audio_service, audio_semantic_timeline, audio_voice_enhance, audio_field_to_samples) [conservative].
- Prod-lite: majority (~45) with working code + tests/in-memory repos but missing hardening/auth/persistence.
- Stub/prototype: ~17 (CLI runners, alignment stubs, billing/seo stubs, reactive/animation, anonymise/backend-less tools).
- Biggest gaps: consistent multi-tenant enforcement/auth across routes; replacing stub DSP backends (alignment/animation/anonymise/ingest); persistence beyond in-memory for many services; failure-mode/tests for CLI engines; stronger logging/audit for safety/budget/kpi integration.

