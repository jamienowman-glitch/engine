## Placement
- Host the MCP Gateway inside this repo as a sibling FastAPI app (e.g., `engines/mcp_gateway/server.py`) so it can import routers/services directly and reuse `RequestContext`/`ErrorEnvelope` helpers (`engines/common/identity.py`, `engines/common/error_envelope.py`). Sidecar avoids duplicating auth/error semantics and keeps tool inventory co-located with routing metadata already validated at startup (`engines/chat/service/server.py:70`).
- Avoid a separate repo until engines stabilize; the engines app already centralizes CORS and router mounting, so a dedicated MCP process can mount specific routers or call services in-process without HTTP hops.

## Invocation Types to Wrap First
- HTTP sync routes are the lowest-friction: chat store (`engines/chat/service/routes.py`), media_v2 (`engines/muscle/media_v2/routes.py`), budget (`engines/budget/routes.py`), raw_storage (`engines/nexus/raw_storage/routes.py`).
- HTTP async/poll: expose `video_render` job submit/get (`engines/muscle/video_render/routes.py:103`, :137) as `tools.call` + `tools.get_status`.
- Streaming: SSE/WS transports (chat/canvas) can be wrapped as MCP streaming tools by piping `StreamEvent` chunks (`engines/chat/service/sse_transport.py:166`, `engines/canvas_stream/router.py:202`); implement after HTTP paths because cursor/ticket handling needs translation.

## Error Mapping
- Preserve canonical `ErrorEnvelope` (`engines/common/error_envelope.py:13`) by placing it in `error.data` of JSON-RPC responses; map `error.error.http_status` to JSON-RPC `code` and keep `message` identical.
- For routes without envelope handlers, wrap HTTPException to `ErrorEnvelope` via shared helper (reuse `_http_exception_handler` in `engines/chat/service/http_transport.py:123`).

## Identity Propagation
- Forward bearer `Authorization` and `X-Mode/X-Tenant-Id/X-Project-Id/...` headers into `RequestContextBuilder` (`engines/common/identity.py:73`); reject requests missing `X-Mode` per builder contract.
- For ticket-based transports (chat/canvas SSE/WS), translate MCP session auth into ticket issuance/validation using `context_from_ticket` (`engines/identity/ticket_service.py`) before opening streams.

## Tool Schema Strategy
- Prefer auto-generating schemas from Pydantic models via `model_json_schema()` for routes that declare request bodies (e.g., `ChatAppendRequest` at `engines/chat/service/routes.py:18`, `MediaUploadRequest` at `engines/muscle/media_v2/models.py:119`, `RenderRequest` at `engines/muscle/video_render/models.py:44`).
- Hand-author schema blobs for endpoints using raw UploadFile/forms (e.g., `canvas_artifacts` upload at `engines/canvas_artifacts/router.py:11`, `vector_explorer` ingest form at `engines/nexus/vector_explorer/ingest_routes.py:26`), and for transports where the payload is stream events rather than JSON.
- Include identity/budget metadata fields explicitly in schema descriptions so MCP clients set `X-*` headers correctly.
