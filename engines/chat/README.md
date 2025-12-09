# Universal Chat Stubs (PLAN-024)

This directory contains repo-only stubs for a universal chat system. No external services, LLMs, or databases are used; everything is in-memory for front-end development and integration tests. Messages can carry a scope (surface/app/federation/cluster/gang/agent) and are routed accordingly; unscoped messages default to surface/app orchestrator.

## Components
- `contracts.py` – Pydantic models for `Thread`, `Message`, `Contact`.
- `service/http_transport.py` – FastAPI HTTP endpoints for threads/messages with stubbed agent echo.
- `service/ws_transport.py` – WebSocket endpoint `/ws/chat/{thread_id}` broadcasting messages to subscribers.
- `service/sse_transport.py` – SSE endpoint `/sse/chat/{thread_id}` streaming message events.
- Scope schema (carried on messages/logging):
```json
{
  "surface": "chat_surface",
  "app": "caidence2",
  "federation": "fed_main",
  "cluster": "orchestration_cluster",
  "gang": "marketing",
  "agent": "ceo_agent",
  "kind": "federation",
  "target_id": "fed_main"  // legacy single-scope fields still supported
}
```
Scope fields are logged to Nexus and DatasetEvents; tags include all populated scope dimensions.

Modes:
- On-demand: current HTTP/WS/SSE endpoints.
- Scheduled: future planner jobs will enqueue messages (not implemented here yet).
- Reactive: DatasetEvent-driven flows (see docs/engines/REACTIVE_CONTENT.md) can create new messages/events.
- `service/transport_layer.py` – In-memory pub/sub used by all transports.
- `service/server.py` – Aggregate FastAPI app including HTTP, WS, and SSE routers.

## Running locally
```bash
uvicorn engines.chat.service.server:app --reload --port 8082
```

This is a stub implementation for local development. Data is transient. Behaviour is limited to echo replies from a stub agent in HTTP `POST /chat/threads/{id}/messages`. Replace or extend with real agents/transports later.
