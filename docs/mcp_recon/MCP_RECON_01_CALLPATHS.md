## chat_service
- What it is: Chat HTTP/SSE/WS rail backed by chat_store bus and Nexus logging for thread messaging.
- Call path: `/chat/threads/{thread_id}/messages` → `append_message` (`engines/chat/service/routes.py:54`) → `publish_message` (`engines/chat/service/transport_layer.py:146`) → chat_store append + realtime bus + timeline store enqueue → optional SSE/WS replay via `subscribe_async` (`engines/chat/service/transport_layer.py:180`) consumed by `/sse/chat/{thread_id}` (`engines/chat/service/sse_transport.py:166`) and `/ws/chat/{thread_id}` (`engines/chat/service/ws_transport.py:219`).
- Identity expectations: Enforced via `RequestContext`/`get_request_context` and `require_tenant_membership` (`engines/chat/service/routes.py:54`, `engines/chat/service/http_transport.py:69`); SSE/WS accept ticket-based context (`engines/chat/service/sse_transport.py:116`, `ws_transport.py:233`).
- Error semantics: HTTP handlers wrap errors with canonical envelope builders (`engines/chat/service/http_transport.py:101`, `_http_exception_handler` at :123); chat routes use `error_response`/`missing_route_error` (`engines/chat/service/routes.py:81`).
- Artifact semantics: Persists chat messages to chat_store timeline and emits `StreamEvent` envelopes (`engines/chat/service/transport_layer.py:157`, :173); no media_v2 artifacts.
- View model support: Streams `StreamEvent` for UI consumers; no dedicated view model.

## canvas_stream
- What it is: SSE stream for canvas events reusing chat_store history/resume.
- Call path: `/sse/canvas/{canvas_id}` → `stream_canvas` (`engines/canvas_stream/router.py:202`) → `_canvas_stream_with_resume` (:202-233) → chat_store cursor check + `_format_sse_event` built from `StreamEvent` via `subscribe_canvas` (`engines/canvas_stream/service.py` usage in router).
- Identity expectations: `_canvas_context` depends on `get_request_context` or ticket (`engines/canvas_stream/router.py:120`); `verify_canvas_access` enforces tenant match (`engines/canvas_stream/router.py:225`).
- Error semantics: Uses `error_response`/`cursor_invalid_error` for auth/cursor failures (`engines/canvas_stream/router.py:210`, :33).
- Artifact semantics: Streams realtime `StreamEvent` only; history stored in chat_store; no artifact registration.
- View model support: SSE feed consumed by canvas UI; no server-side view models.

## canvas_artifacts
- What it is: Upload endpoint for canvas asset blobs returning simple refs.
- Call path: `/canvas/{canvas_id}/artifacts` → `upload_canvas_artifact` (`engines/canvas_artifacts/router.py:11`) → `upload_artifact` (`engines/canvas_artifacts/service.py:5`) → `InMemoryArtifactStorage.upload` (`engines/canvas_artifacts/storage.py:16`).
- Identity expectations: Requires `RequestContext` + `AuthContext` tenant match only (`engines/canvas_artifacts/router.py:15`).
- Error semantics: Plain HTTPException on tenant mismatch; no envelope.
- Artifact semantics: Stores bytes under in-memory key → returns `ArtifactRef` (`engines/canvas_artifacts/models.py:8`); no media_v2 registration/durability.
- View model support: none.

## media_v2_assets
- What it is: Canonical media asset/artifact registry with S3/Firestore backends.
- Call path: `/media-v2/assets` → `create_media_asset` (`engines/muscle/media_v2/routes.py:32`) → `MediaService.register_upload/register_remote` (`engines/muscle/media_v2/service.py:193` et al); `/media-v2/assets/{asset_id}/artifacts` → `register_artifact` (`engines/muscle/media_v2/routes.py:104`) → repo `create_artifact` (S3/Firestore) (`engines/muscle/media_v2/service.py:216`).
- Identity expectations: `require_tenant_membership` + `assert_context_matches` on tenant/env (`engines/muscle/media_v2/routes.py:42`, :89).
- Error semantics: Plain HTTPException; no envelope normalization.
- Artifact semantics: Creates `MediaAsset`/`DerivedArtifact` records with S3 URI or local tmp fallback (`engines/muscle/media_v2/service.py:62`, :108); supports artifact kinds for video/audio/image/cad.
- View model support: unknown; no dedicated view models in code.

## audio_service
- What it is: Audio preprocessing/ASR/beat/align/voice-enhance pipeline writing artifacts.
- Call path: `/audio/*` routes (`engines/muscle/audio_service/routes.py:23`) → `AudioService` methods (`engines/muscle/audio_service/service.py:57` etc.) → audio engines (ffmpeg/whisper) → `_register_output` writing media_v2 artifacts (`engines/muscle/audio_service/service.py:97`).
- Identity expectations: `get_request_context` + `require_tenant_membership` on every route (`engines/muscle/audio_service/routes.py:23`).
- Error semantics: HTTPException with raw string detail (`engines/muscle/audio_service/routes.py:31`); no envelope.
- Artifact semantics: Reads media_v2 assets/artifacts, emits `ArtifactCreateRequest` for kinds `audio_clean`, `audio_segment`, `beat_features`, `asr_transcript`, `bars`, `voice_enhance` (`engines/muscle/audio_service/service.py:104`, :133, :157, :188, :214).
- View model support: none.

## audio_semantic_timeline
- What it is: Audio semantic analysis (speech/music/beat) producing timeline artifacts.
- Call path: `/audio/semantic-timeline/analyze` → `analyze_audio_semantic` (`engines/muscle/audio_semantic_timeline/routes.py:15`) → `AudioSemanticService.analyze` (`engines/muscle/audio_semantic_timeline/service.py:59`+) → backend (whisper/librosa) → media_v2 artifact registration (`engines/muscle/audio_semantic_timeline/service.py`, uses `ArtifactCreateRequest`).
- Identity expectations: None (routes accept raw payload, no RequestContext/Auth).
- Error semantics: HTTPException 404/500 only (`engines/muscle/audio_semantic_timeline/routes.py:15`).
- Artifact semantics: Registers `audio_semantic_timeline` artifacts in media_v2 with summary JSON (`engines/muscle/audio_semantic_timeline/models.py:33`, service uses GCS upload).
- View model support: none.

## video_render
- What it is: Timeline-based video rendering + chunked jobs producing render artifacts.
- Call path: `/video/render` → `render` (`engines/muscle/video_render/routes.py:44`) → `RenderService.render` (`engines/muscle/video_render/service.py:1236`) → plan build/ffmpeg execute → `_register_render_output` media_v2 artifact (`engines/muscle/video_render/service.py:1227`). Job routes call `create_job/run_job` on `VideoRenderJobRepository` (`engines/muscle/video_render/routes.py:103`, :150).
- Identity expectations: `get_request_context` + `require_tenant_membership` + `assert_context_matches` on tenant/env (`engines/muscle/video_render/routes.py:26`).
- Error semantics: HTTPException with raw detail; no envelope.
- Artifact semantics: Consumes timeline state/media assets, writes media_v2 artifacts `render`/`render_segment` with cache metadata (`engines/muscle/video_render/service.py:1227`, :1252).
- View model support: plan preview returned in `RenderResult`; no UI view models.

## video_timeline
- What it is: CRUD for projects/sequences/tracks/clips/filter stacks/automation with Firestore repo.
- Call path: `/video/projects` etc. → `router` handlers (`engines/muscle/video_timeline/routes.py:40` etc.) → `TimelineService` → `FirestoreTimelineRepository` persistence (`engines/muscle/video_timeline/service.py:436` / :522).
- Identity expectations: `get_request_context` + `require_tenant_membership` + `assert_context_matches` enforce tenant/project (`engines/muscle/video_timeline/routes.py:19`).
- Error semantics: HTTPException only (400/404) (`engines/muscle/video_timeline/routes.py:92`).
- Artifact semantics: Timeline data only; no media_v2 linkage.
- View model support: Gantt view endpoint `/video/view/gantt` returning `GanttView` model (`engines/muscle/video_timeline/router.py:93` in legacy file) via service.

## video_regions
- What it is: Video region detection (face/skin/etc.) with caching via media artifacts.
- Call path: `/video/regions/analyze` → `analyze_regions` (`engines/muscle/video_regions/routes.py:37`) → `VideoRegionsService.analyze_regions` (`engines/muscle/video_regions/service.py:18`) → backend (Real/Cpu/Stub) → media_v2 artifact registration/listing (`engines/muscle/video_regions/service.py:35`, :51).
- Identity expectations: `get_request_context` + `require_tenant_membership` + `assert_context_matches` (`engines/muscle/video_regions/routes.py:21`).
- Error semantics: HTTPException (400/404) only (`engines/muscle/video_regions/routes.py:52`, :65).
- Artifact semantics: Reads media_v2 asset, emits `video_region_summary` artifact with meta cache key/backend version (`engines/muscle/video_regions/service.py:33`, :56).
- View model support: Returns `RegionAnalysisSummary`; no UI adapters.

## vector_explorer
- What it is: Vector corpus query + ingest over Firestore + Vertex vector store.
- Call path: `/vector-explorer/scene` → `get_vector_scene` (`engines/nexus/vector_explorer/routes.py:32`) → `VectorExplorerService.build_scene_from_query` (service module) → repository/vector_store/adapters; ingest `/vector-explorer/ingest` → `ingest_vector_item` (`engines/nexus/vector_explorer/ingest_routes.py:26`) → `VectorIngestService.ingest`.
- Identity expectations: `get_request_context` + `require_tenant_membership`; ingest gated by strategy_lock (`engines/nexus/vector_explorer/ingest_routes.py:35`).
- Error semantics: HTTPException with raw detail; no envelope (`engines/nexus/vector_explorer/routes.py:55`).
- Artifact semantics: Writes corpus items with `vector_ref` and GCS URI (service); no media_v2 usage.
- View model support: Returns scene graph response (`VectorExplorerResult`) consumed by UI; no explicit view model layer.

## raw_storage
- What it is: Object store presign/register/put/get with routing-based backend.
- Call path: `/nexus/raw/presign-upload` → `presign_upload` (`engines/nexus/raw_storage/routes.py:28`) → `ObjectStoreService.presign_upload`; `/nexus/raw/register` → `register_asset` (:43) → repo; `/nexus/raw/put|get` direct to `ObjectStoreService.put/get` (`engines/nexus/raw_storage/routing_service.py`).
- Identity expectations: `enforce_tenant_context` + GateChain on presign/register (`engines/nexus/raw_storage/routes.py:28`); put/get only need `RequestContext`.
- Error semantics: HTTPException; ForbiddenBackendClass surfaced as 403 (`engines/nexus/raw_storage/routes.py:86`).
- Artifact semantics: Manages `RawAsset` records (sha/size/uri) (`engines/nexus/raw_storage/models.py:21`); stores raw bytes in configured backend.
- View model support: none.

## cad_ingest
- What it is: CAD ingest/healing pipeline producing cad_model artifact.
- Call path: `/cad/ingest` → `ingest_cad_file` (`engines/muscle/cad_ingest/routes.py:31`) → `CadIngestService.ingest` (`engines/muscle/cad_ingest/service.py:61`) → adapter parse + topology heal → `register_artifact` to media_v2 (`engines/muscle/cad_ingest/service.py:177`).
- Identity expectations: `get_request_context` + `assert_context_matches`; `AuthContext` required (`engines/muscle/cad_ingest/routes.py:43`).
- Error semantics: HTTPException 400/500 only.
- Artifact semantics: Registers `cad_model` artifact via media_v2 (`engines/muscle/cad_ingest/service.py:177`); caches models in-memory.
- View model support: none.
- Note: Router not mounted in main `create_app` (`engines/chat/service/server.py`); currently unreachable from primary service.

## marketing_cadence
- What it is: Marketing content pool/asset registry + schedule generator (MC01) stored in-memory.
- Call path: `/api/cadence/pools/register` etc. → route handlers (`engines/marketing_cadence/routes.py:46`) → `CadenceService` in-memory maps (`engines/marketing_cadence/service.py:94`, :128, :171).
- Identity expectations: None; tenant/env validated only from payload (`engines/marketing_cadence/routes.py:33`).
- Error semantics: HTTPException on validation; no envelope.
- Artifact semantics: No media/artifact integration; schedules returned inline.
- View model support: none.
- Note: Not mounted in main create_app; standalone only.

## scene_engine
- What it is: Standalone scene layout engine turning grid/boxes into scene graph nodes.
- Call path: `/scene/build` → `build_scene` (`engines/scene_engine/service/routes.py:17`) → `map_boxes` (`engines/scene_engine/core/mapping.py`) → `SceneBuildResult` (`engines/scene_engine/core/types.py:92`).
- Identity expectations: None; no RequestContext/Auth.
- Error semantics: Pure function; no custom envelope.
- Artifact semantics: In-memory scene graph only; export options live under `engines/scene_engine/export`.
- View model support: Scene view/render models exist (`engines/scene_engine/view/service.py`), but not wired to HTTP.
- Note: Separate FastAPI app (`engines/scene_engine/service/server.py`); not mounted into main server.

## image_core
- What it is: Image composition/rendering plus presets/templates producing image artifacts.
- Call path: `/image/render` → `render_composition` (`engines/muscle/image_core/routes.py:86`) → `ImageCoreService.render_composition` (service module) → media_v2 artifact creation for `image_render`/`image_composition` (service uses media service).
- Identity expectations: None; routes take raw payloads (no RequestContext/Auth).
- Error semantics: HTTPException 500 on failure (`engines/muscle/image_core/routes.py:112`).
- Artifact semantics: Emits media_v2 artifacts with render metadata; parent_asset optional (`engines/muscle/image_core/routes.py:105`).
- View model support: Composition templates/presets (`engines/image_core/template_models.py`) act as view-layer data.

## budget_usage
- What it is: Budget usage logger/policy CRUD with FS/in-memory repo.
- Call path: `/budget/usage` → `post_usage` (`engines/budget/routes.py:32`) → `BudgetService.record_usage` (`engines/budget/service.py:17`) → repo (`engines/budget/repository.py:14`); policy routes use `BudgetPolicyRepository` (`engines/budget/repository.py:144`).
- Identity expectations: `get_request_context` + `require_tenant_membership` + `assert_context_matches` on events (`engines/budget/routes.py:32`).
- Error semantics: Uses `error_response` for auth errors; otherwise HTTPException/plain dicts.
- Artifact semantics: No media artifacts; persists cost events to memory/FS JSONL; attaches aws metadata if provider=aws (`engines/budget/service.py:41`).
- View model support: none.

