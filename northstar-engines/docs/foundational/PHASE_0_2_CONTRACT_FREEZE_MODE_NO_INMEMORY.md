# Phase 0→2 Contract Freeze — Mode + No-InMemory (Authoritative, DOCS ONLY)

Authoritative sources (repo reality):
- RequestContext builder: engines/common/identity.py:22-151.
- Auth guard: engines/identity/auth.py:13-54.
- Stream transports: engines/chat/service/sse_transport.py:23-68; ws_transport.py:136-205; transport_layer.py:65-121.
- Event schemas: engines/dataset/events/schemas.py:9-32; engines/realtime/contracts.py:74-165.

## Canonical RequestContext (must-be)
- Required: tenant_id (regex ^t_[a-z0-9_-]+$), mode (saas|enterprise|lab), project_id, request_id (auto-generate if missing).
- Optional: surface_id, app_id, user_id/actor_id, membership_role, canvas_id (not in code; add when present).
- Headers (current code uses X-Env → must be X-Mode):  
  - X-Tenant-Id, X-Mode, X-Project-Id, X-Surface-Id, X-App-Id, X-User-Id, X-Membership-Role, X-Request-Id.
- Precedence (as implemented today): headers > query fallbacks > body fallback; JWT overlays tenant/user/role. Contract delta: remove body fallback except guarded legacy flag; enforce X-Mode; reject legacy env values (dev/staging/prod/stage).
- Only hardcoded tenant allowed: t_system (bootstrap: engines/identity/routes_auth.py:82-107).

## Auth rules (HTTP/SSE/WS)
- HTTP: Authorization: Bearer required on protected routes; validated via default_jwt_service or Cognito verifier (engines/identity/auth.py:13-35); 401 on missing/invalid.
- SSE/WS: Must accept Authorization header; client must send X-Tenant-Id + X-Mode + X-Project-Id (and surface/app if required). No ?token support unless explicitly added (not present today). Tenant membership enforced; project/app currently not enforced in transports.
- Actor model: If JWT present, actor_id/user_id derived from token; client cannot override. If no token (legacy), client-supplied user_id allowed but should be deprecated. Agents/tools identified explicitly (e.g., agentId="vector_explorer" in events).

## Event/logging envelope (minimum fields required)
- DatasetEvent today: tenantId/env/surface/agentId/input/output/metadata/pii_flags/train_ok/traceId/requestId/actorType (engines/dataset/events/schemas.py:9-32). Required delta: replace env with mode; add project_id, app_id, surface_id (structured), run_id, step_id, schema_version, severity, storage_class.
- StreamEvent today: routing.tenant_id/env/actor_id + meta.persist (engines/realtime/contracts.py:74-165). Required delta: add mode, project_id, app_id, surface_id, run_id/step_id/schema_version/severity; ensure ids include request_id/trace_id.
- Correlation: All emitted events must carry tenant_id + mode + project_id + request_id + trace_id minimum; no emit without full scope.

## Storage/routing rules (no in-memory)
- In-memory/noop backends/buses/loggers are forbidden (including tests). Current violations: memory repo default InMemory (engines/memory/repository.py:104-111); nexus memory uses in-memory dict (engines/nexus/memory/service.py:16-72); chat bus replay in-memory/Redis (engines/chat/service/transport_layer.py:65-121); vector explorer event logger defaults to no-op (service.py:167-175; ingest_service.py:32-47); budget repo in-memory default (engines/budget/repository.py:175-182).
- Startup must fail fast if durable backends missing (repos, bus, audit/log sinks, vector store, raw storage buckets). Tests must run against real isolated durable targets.

## PII boundary (contract)
- PII must be stripped before any LLM/tool/embedding call. Current gap: chat/service/llm_client.py:27-50; engines/nexus/vector_explorer/service.py:107-135; ingest_service.py:168-188 send raw text.
- Logging engine masks PII before Nexus persistence (engines/logging/events/engine.py:17-46); must be extended to pre-call and support rehydration hooks (tenant-authorized).

## Mode replaces env (explicit)
- Legacy env values (dev/staging/prod/stage) are invalid for the frozen contract. X-Mode required; mode values exactly saas|enterprise|lab. Any routing/env normalization must be refactored to mode.***
