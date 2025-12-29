# Phase 0→2 UI Compliance Notes (Mode + No-InMemory)

What must change
- Transport headers: every request (HTTP, SSE, WS, fetch, graph) must send X-Mode (saas|enterprise|lab), X-Tenant-Id, X-Project-Id, plus X-Surface-Id/X-App-Id/X-User-Id/X-Request-Id when available. Authorization header required for SSE/WS; no ?token fallbacks.
- Actor_id: when JWT is present, UI must not override actor_id/user_id; use token subject. If unauth flows remain, they must be explicitly gated and documented.
- Replay: clients must handle durable resume via Last-Event-ID (SSE) or last_event_id (WS) with stable cursor; in-memory-only replay is noncompliant—assume server provides durable timeline.
- Mode replaces env: remove dev/staging/prod assumptions from configs; choose mode per tenant/session and pass X-Mode. UI config/env vars must map to saas|enterprise|lab only.
- PII boundary: do not send raw PII to LLM/tool endpoints; ensure client-side logging/telemetry excludes PII or applies the same redaction policy; avoid storing prompts in local caches.

Do-not-break
- Visible work proofs and optimistic interactions: preserve UX flows but attach required headers.
- Existing canvas/editor state flows: ensure added headers/Authorization do not break current fetch/WS/SSE calls.
- Keep import paths and build tooling unchanged; limit changes to transport wrappers/config.

Evidence pointers (server expectations)
- RequestContext headers (engines/common/identity.py:43-51) — replace X-Env with X-Mode.
- SSE/WS transports expect Authorization header and request context (engines/chat/service/sse_transport.py:44-58; ws_transport.py:136-205).
