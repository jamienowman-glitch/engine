# PHASE 02 — Realtime Rails Foundation (SSE + WS)

Goal: Both rails exist with strict routing keys and isolation: WS for chat/tool/presence; SSE for canvas commits/artifact notifications/gesture fanout. Reconnect/resume semantics required.

In-scope
- Extend existing WS/SSE transports to enforce RequestContext, auth, routing keys, and reconnection behavior.
- Presence/heartbeat for WS; Last-Event-ID/cursor for SSE.
- Isolation tests: tenant/env/workspace/project/app/surface/canvas/projection/panel/thread/actor.

Out-of-scope
- UI, orchestration, token semantics beyond transport envelope.
- CRDT/OT logic; only transport and routing.

Allowed modules to change
- `engines/chat/service/ws_transport.py`, `sse_transport.py`, `transport_layer.py`, `server.py`.
- New module for canvas SSE stream (e.g., `engines/canvas_stream/*`) following FastAPI router pattern.
- `engines/common/identity.py` (only if needed for routing key helpers).
- Tests under `engines/chat/tests` and new canvas_stream tests.

Steps
1) WS rail (chat/presence/tool events):
   - Add RequestContext + `get_auth_context` dependencies; reject missing/tenant mismatch.
   - Expand envelope to include routing keys (tenant_id, env, workspace_id, project_id, app_id, surface_id, canvas_id, projection_id, panel_id, thread_id, actor_id).
   - Add heartbeat/ping and presence state per routing key; rejoin by sending resume token/thread_id.
2) SSE rail (canvas commits/artifact notifications/gestures):
   - New SSE router with strict routing keys and auth.
   - Support Last-Event-ID / cursor for replay from in-memory buffer (bounded) or persisted log.
   - Channels: commits (authoritative), artifact notifications (preview/replay/audit), optional gesture fanout (configurable via Tenant-0 flags).
3) Isolation:
   - Server-side verification of routing keys matches RequestContext tenant/env.
   - Ensure no cross-talk between different canvas IDs or tenants.
4) Tests:
   - WS: two tenants cannot receive each other’s messages; heartbeat/presence keeps connection alive; resume rejoins after reconnect.
   - SSE: Last-Event-ID replays buffered events; cross-tenant isolation; auth required.
5) Stop conditions:
   - DO NOT continue if transports still accept connections without RequestContext/auth.
   - DO NOT continue if routing keys are not validated server-side.

Do not touch
- No prompt/persona/LLM behavior; no CRDT logic; no FE code.
