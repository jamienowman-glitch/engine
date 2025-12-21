# PHASE_01_STREAMING_AUTH_AND_ISOLATION

## Goal
Lock SSE and WebSocket transports so every connection uses `RequestContext` + `AuthContext`, validates thread/canvas routing via `verify_thread_access`/`verify_canvas_access`, propagates `request_id`/`trace_id`, and exposes resume semantics (Last-Event-ID for SSE, explicit last_event_id/token for WS).

## In-scope / Out-of-scope
- **In-scope:** `engines/chat/service/ws_transport.py`, `engines/chat/service/sse_transport.py`, `engines/realtime/isolation.py`, new tests under `engines/chat/service/tests`, `engines/common/identity.py` (only if required to add helper for trace_id). 
- **Out-of-scope:** media engines, FE code, any non-WS/SSE transports, chat HTTP transport (handled elsewhere).

## Required invariants
1. Every SSE/WS handler must declare `Depends(get_request_context)` and `Depends(get_auth_context)`; fail if tenant mismatch or missing env.
2. Trace IDs (`RequestContext.request_id`) flow into each emitted `StreamEvent` metadata so SSE/WS consumers can correlate.
3. Routing verification uses `verify_thread_access`/`verify_canvas_access` and returns 403/404 as described in spec.
4. Resume support uses `Last-Event-ID` header (SSE) and explicit payload field + server-supplied cursor (WS) for replay.

## Allowed modules to change
- `engines/chat/service/ws_transport.py`
- `engines/chat/service/sse_transport.py`
- `engines/realtime/isolation.py`
- `engines/chat/service/tests/*`
- `engines/common/identity.py` (only to expose helper for trace_id / correlation)

## Step-by-step tasks
1. Remove the duplicate no-auth SSE router near the bottom of `sse_transport.py` and ensure the exported router uses the authenticated handler only.
2. Update SSE handler to depend on `RequestContext` + `AuthContext`, require tenant match, enforce `verify_thread_access`, and set `RoutingKeys` with tenant/env from context; add Last-Event-ID propagation for resume (store last_event_id in `StreamEvent.meta` and handle replays by passing through `subscribe_async`).
3. Update WS transport to require token-derived `AuthContext` + headers for `RequestContext`, enforce tenant/env match, validate via `verify_thread_access`, and move heartbeat/resume logic to use request trace IDs; emit `trace_id` metadata on each broadcasted `StreamEvent`.
4. Add unit tests in `engines/chat/service/tests` verifying SSE/WS reject missing auth headers, mismatch tenants, enforce `verify_thread_access`, and include Last-Event-ID/resume semantics.
5. Update `engines/realtime/isolation.py` registry helpers to expose `register_thread`/`register_canvas` results used during tests (no behavioral change) and ensure `validate_routing` uses `RequestContext` env strictness.
6. Document in-phase README (if existing) that SSE/WS now require auth (update doc string at top of SST file if necessary).

## Tests
- `pytest engines/chat/service/tests/test_sse_transport.py::test_authenticated_stream_mounts` (validates auth/tenant match, Last-Event-ID resume).
- `pytest engines/chat/service/tests/test_ws_transport.py::test_ws_rejects_missing_context` (ensures JWT + RequestContext required, verifies `verify_thread_access` path). 

## Acceptance criteria
- SSE connections without `Authorization` or `X-Tenant-Id` header fail with 401/403 before any stream data.
- WS handshake fails quickly if tenant mismatch or `verify_thread_access` rejects the thread; valid clients receive traceable `StreamEvent` payloads containing `trace_id`.
- Replay/resume semantics accept `Last-Event-ID` (SSE) and server-provided cursor (WS) via failing test coverage.

## Stop conditions
- If adding authentication requires touching modules outside the allowed list (e.g., FE or chat HTTP transport), stop and escalate before continuing.
- If `verify_thread_access` changes require datastore additions, halt once detection occurs and record in risk register.

## Do-not-touch list
- `engines/chat/service/http_transport.py`
- `engines/bossman/routes.py`
- UI code outside allowed modules.

## Mini execution guardrails
- If any file outside the allowed modules must change, STOP and report before modifying.
