## chat_service
- Identity: Uses `get_request_context` + `require_tenant_membership` for HTTP/SSE/WS (engines/common/identity.py; engines/chat/service/routes.py; sse_transport.py).
- Errors: HTTP transport registers `register_error_handlers`; other routes use `error_response` but some raw HTTPExceptions remain.
- Persistence: chat_store bus/timeline; storage backend not durable by default (likely in-memory); restart safety unproven.
- Streaming: SSE/WS resume uses chat_store cursor; no durable replay.
- Observability: No budget/audit or gatechain except chat_send gate_chain.

## canvas_stream
- Identity via `_canvas_context` (get_request_context or ticket) but does not enforce project/app strictly.
- Errors via `error_response` for auth and cursor_invalid; other exceptions raw.
- Uses chat_store for history; in-memory; restart replay not durable.

## canvas_artifacts
- Minimal identity (tenant match only) and no RequestContext enforcement.
- In-memory storage `InMemoryArtifactStorage`; not durable.
- Raw HTTPExceptions; no error envelope; no observability hooks.

## media_v2_assets
- Identity enforced via RequestContext + auth.
- Errors are raw HTTPExceptions; no register_error_handlers.
- Persistence via Firestore/S3 repo and S3/Local storage; LocalMediaStorage fallback if RAW_BUCKET missing (in-memory temp).
- Artifacts lack pipeline_hash/backend_version meta; no budget/audit.

## audio_service
- Identity enforced on routes; service uses media_v2 + FFmpeg/ASR backends.
- Errors raw HTTPExceptions; no error envelope mapper.
- Artifacts registered in media_v2 with limited meta; no pipeline_hash.
- No budget/audit/gatechain; durability relies on media_v2.

## audio_semantic_timeline
- No RequestContext/Auth in routes; raw HTTPExceptions.
- Uses local file IO + media_v2 artifacts; no pipeline_hash/backend_version enforcement.
- No budget/audit.

## video_render
- Identity enforced; errors raw.
- Uses media_v2; render outputs carry cache key but no pipeline_hash field.
- No budget/audit; jobs synchronous; restart safety unknown; backend FFmpeg/Timeline dependencies.

## video_timeline
- Identity enforced; errors raw.
- Persistence via Firestore only; no guard for missing config; in-memory fallback not allowed but not enforced.
- No budget/audit; no media linkage validation.

## video_regions
- Identity enforced; errors raw.
- Uses media_v2 artifacts for caching; backend can be stub/real/opencv; no budget/audit.

## cad_ingest
- Identity enforced; not mounted in main app.
- Artifacts via media_v2; cache in memory; remote source ingest unimplemented.
- Errors raw; no budget/audit/gatechain.

## vector_explorer
- Identity enforced; ingest gated by strategy_lock; errors raw.
- Persistence via Firestore/Vertex; no budget/audit; query lacks gatechain.

## raw_storage
- Identity enforced via enforce_tenant_context + GateChain on presign/register; put/get lack auth beyond RequestContext.
- Errors raw; persistence routed but may allow filesystem backend; no budget/audit.

## image_core
- No RequestContext/Auth; raw errors.
- Uses media_v2 implicitly; no pipeline_hash/backends recorded; no budget/audit.

## scene_engine
- Standalone app; no identity/auth; raw errors.
- In-memory only; no persistence/observability; restart safety missing.

## marketing_cadence
- No identity/auth; in-memory storage; raw errors.
- No durability or observability.

## budget_usage
- Identity enforced; auth errors wrapped with `error_response`; other errors raw.
- Persistence in-memory/FS; no durable store for saas.
- Budget events recorded themselves; no audit; gatechain absent.
