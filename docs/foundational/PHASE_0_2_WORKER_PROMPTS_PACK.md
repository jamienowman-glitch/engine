# Worker Prompts Pack (Engines) — Mode-only, No-InMemory

## Worker 1 — Mode-only RequestContext
Scope: /Users/jaynowman/dev/northstar-engines  
Do-not-break: identity_repo defaults; auth decode; headers casing.  
Tasks: replace X-Env with X-Mode; validate saas|enterprise|lab; reject legacy env; remove body fallback unless guarded legacy flag; ensure SSE/WS use same headers.  
DoD: tests for context builder reject missing/legacy env and accept mode; SSE/WS pass headers through.  
Commands: pytest (add) tests/context/test_mode_headers.py.

## Worker 2 — No in-memory/no noop enforcement
Scope: engines/memory/repository.py; engines/nexus/memory/service.py; engines/budget/repository.py; engines/chat/service/transport_layer.py; engines/nexus/vector_explorer/service.py logger init.  
Do-not-break: public APIs and router wiring.  
Tasks: remove/guard InMemory/Noop defaults; fail-fast startup when durable missing; ensure event logger non-noop.  
DoD: tests/test_real_infra_enforcement.py passes; in-memory configs raise at init.

## Worker 3 — PII pre-call boundary
Scope: engines/chat/service/llm_client.py; engines/nexus/vector_explorer/service.py; engines/nexus/vector_explorer/ingest_service.py; shared redaction hook.  
Do-not-break: existing call signatures and Vertex wiring.  
Tasks: redact inputs before LLM/tool/embedding; log pii_flags/train_ok; add rehydration hook stub; ensure logged events use redacted payload.  
DoD: tests/logs/test_pii_gate.py.

## Worker 4 — Durable stream replay
Scope: engines/chat/service/transport_layer.py; sse_transport.py; ws_transport.py; new durable timeline store.  
Do-not-break: StreamEvent shape and auth.  
Tasks: persist stream events; resume via Last-Event-ID/last_event_id from storage; remove in-memory replay path.  
DoD: tests/logs/test_stream_replay.py (resume after restart).

## Worker 5 — Event envelope completeness + no silent-drop loggers
Scope: engines/dataset/events/schemas.py; engines/realtime/contracts.py; emitters (chat/pipeline.py; vector_explorer/service.py; ingest_service.py; logging/events/engine.py).  
Do-not-break: business logic.  
Tasks: add mode/project/app/surface/run/step/schema_version/severity/storage_class; populate in emitters; ensure loggers fail on missing scope (no no-op).  
DoD: tests/logs/test_event_contract.py.

## Worker 6 — Memory durability + scoping
Scope: engines/memory/repository.py/service.py; engines/nexus/memory/routes.py/service.py.  
Do-not-break: /memory and /nexus/memory APIs.  
Tasks: enforce durable backend only; persist tenant/mode/project/user/session; remove in-memory dict/backends.  
DoD: tests/memory/test_memory_persistence.py.

## Worker 7 — HAZE/vector explorer alignment
Scope: engines/nexus/vector_explorer/service.py; ingest_service.py; repository.py; vector_store.py.  
Do-not-break: route shapes; StrategyLock gating; Vertex configs.  
Tasks: require mode headers; emit full envelope; inject durable logger; apply PII redaction before embeddings; ensure usage events include run/step/model/tool; remove noop.  
DoD: tests/vector_explorer/test_contract_mode.py.
