## Discovery scope
- Searched `engines/muscle/**` plus `engines/**/routes.py`, `**/server.py`, `**/service.py` for FastAPI routers/apps and callable service entrypoints.
- Main mounted app: `engines/chat/service/server.py:create_app` mounts `http_app` and includes many routers (chat, media_v2, audio_service, video_render, video_timeline, video_regions, audio_semantic_timeline, video_multicam, video_visual_meta, video_mask, video_presets, video_text, video_360, canvas_stream, canvas_artifacts, raw_storage, vector_explorer, nexus settings/index/packs/runs/cards/atoms, budget, billing, kpi, seo, bossman, actions, memory, strategy_lock, identity, analytics_events, kill_switch, ops/status, etc.).
- Standalone apps not mounted: `engines/scene_engine/service/server.py` (scene build), marketing cadence router (`engines/marketing_cadence/routes.py`) with no server wiring in repo, cad_ingest router (`engines/muscle/cad_ingest/routes.py`) defined but not mounted in `create_app`.

## Callable engines (stable ids)
- chat_service — routes in `engines/chat/service/routes.py`, SSE/WS in `engines/chat/service/sse_transport.py`, `ws_transport.py`.
- canvas_stream — SSE routes in `engines/canvas_stream/router.py`.
- canvas_artifacts — upload route in `engines/canvas_artifacts/router.py`.
- media_v2_assets — routes in `engines/muscle/media_v2/routes.py`, service in `engines/muscle/media_v2/service.py`.
- audio_service — routes in `engines/muscle/audio_service/routes.py`, service in `engines/muscle/audio_service/service.py`.
- audio_semantic_timeline — routes in `engines/muscle/audio_semantic_timeline/routes.py`.
- video_render — routes in `engines/muscle/video_render/routes.py`, service in `engines/muscle/video_render/service.py`.
- video_timeline — routes in `engines/muscle/video_timeline/routes.py`, service in `engines/muscle/video_timeline/service.py`.
- video_regions — routes in `engines/muscle/video_regions/routes.py`, service in `engines/muscle/video_regions/service.py`.
- cad_ingest — routes in `engines/muscle/cad_ingest/routes.py` (not mounted).
- vector_explorer — routes `engines/nexus/vector_explorer/routes.py` and ingest `ingest_routes.py`.
- raw_storage — routes in `engines/nexus/raw_storage/routes.py`.
- image_core — routes in `engines/muscle/image_core/routes.py`, service `engines/image_core/service.py`.
- scene_engine — standalone FastAPI app `engines/scene_engine/service/server.py`.
- marketing_cadence — router `engines/marketing_cadence/routes.py` (no main server mount).
- budget_usage — routes in `engines/budget/routes.py`.
