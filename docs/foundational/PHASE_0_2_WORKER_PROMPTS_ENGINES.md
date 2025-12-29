# Worker Prompts — Engines (Mode-only, No-InMemory)

General constraints: ban env (use mode saas|enterprise|lab), ban in-memory/noop, tenant-scoped with only t_system hardcoded, preserve atomic modules, add tests/gates as listed.

1) Worker: Mode-only RequestContext + header contract
- Scope: engines/common/identity.py; any direct uses in transports.
- Tasks: replace X-Env with X-Mode; validate mode values; reject legacy env; remove body fallback unless guarded flag; ensure SSE/WS use same headers.
- Acceptance: add pytest for context builder rejecting missing/legacy env; headers include X-Mode.
- Do-not-break: surface/app defaults via identity_repo; existing auth flow.

2) Worker: No-in-memory/no-noop enforcement + fail-fast startup
- Scope: engines/memory/repository.py; engines/nexus/memory/service.py; engines/budget/repository.py; engines/chat/service/transport_layer.py; vector_explorer logger defaults.
- Tasks: remove/guard in-memory defaults; startup fails if durable backends not configured; event logger cannot be no-op; bus must be durable.
- Acceptance: tests/test_real_infra_enforcement.py (add) ensuring memory/noop rejected; bus/logger durable.
- Do-not-break: keep API signatures; tests must use real isolated durable backends.

3) Worker: PII pre-call boundary for LLM/tool/embedding + rehydration hook
- Scope: engines/chat/service/llm_client.py; engines/nexus/vector_explorer/service.py; ingest_service.py; shared redaction hook.
- Tasks: apply redaction before calls; record pii_flags/train_ok; add rehydration stub; ensure logging uses redacted payload.
- Acceptance: tests/logs/test_pii_gate.py.
- Do-not-break: existing call semantics; avoid leaking raw prompts.

4) Worker: Durable stream replay store + SSE/WS resume
- Scope: engines/chat/service/transport_layer.py; sse_transport.py; ws_transport.py; new durable timeline store module.
- Tasks: persist stream events; resume via Last-Event-ID/last_event_id from storage; remove in-memory replay path.
- Acceptance: tests/logs/test_stream_replay.py (resume after restart).
- Do-not-break: StreamEvent shape; auth checks.

5) Worker: Event envelope completeness + no silent-drop loggers
- Scope: engines/dataset/events/schemas.py; engines/realtime/contracts.py; emitters (chat/pipeline.py; nexus/vector_explorer/service.py; ingest_service.py; logging/events/engine.py).
- Tasks: add mode/project/app/surface/run/step/schema_version/severity/storage_class; populate in emitters; ensure loggers are non-noop and fail on missing scope.
- Acceptance: tests/logs/test_event_contract.py.
- Do-not-break: existing business logic; only envelope.

6) Worker: Memory durability + scoping
- Scope: engines/memory/repository.py/service.py; engines/nexus/memory/routes.py/service.py.
- Tasks: switch to durable backend only; persist tenant/mode/project/user/session; remove in-memory dict and defaults.
- Acceptance: tests/memory/test_memory_persistence.py.
- Do-not-break: API contracts for /memory and /nexus/memory.

7) Worker: HAZE/vector explorer alignment
- Scope: engines/nexus/vector_explorer/service.py; ingest_service.py; repository.py; vector_store.py.
- Tasks: ensure mode headers required; events carry full envelope; event logger injected/durable; PII redaction before embeddings; no in-memory/no-op; usage events complete.
- Acceptance: tests/vector_explorer/test_contract_mode.py.
- Do-not-break: existing route shapes and Vertex wiring; StrategyLock gating.
