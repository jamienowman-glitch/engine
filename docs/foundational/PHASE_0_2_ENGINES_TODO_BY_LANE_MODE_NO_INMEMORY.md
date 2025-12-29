# Phase 0→2 Engines TODO by Lane (Mode-only, No-InMemory)

## Lane A — Spine/Storage/Durability
- **A1: Mode-only RequestContext & headers**  
  Touch points: engines/common/identity.py (replace X-Env with X-Mode; validate saas|enterprise|lab; remove body fallback); transports using get_request_context.  
  Acceptance: pytest target for context builder (add) asserting rejection of legacy env and missing mode.

- **A2: Event envelope completeness**  
  Touch points: engines/dataset/events/schemas.py; engines/realtime/contracts.py; emitters (engines/chat/pipeline.py; engines/nexus/vector_explorer/service.py; ingest_service.py; logging/events/engine.py).  
  Acceptance: pytest tests/logs/test_event_contract.py covering mode/project/app/surface/run/step/schema_version/severity/storage_class.

- **A3: Ban in-memory/noop; fail-fast startup**  
  Touch points: engines/memory/repository.py; engines/nexus/memory/service.py; engines/budget/repository.py; engines/chat/service/transport_layer.py; vector_explorer event logger defaults (service.py:167-175; ingest_service.py:32-47).  
  Acceptance: pytest tests/test_real_infra_enforcement.py ensuring startup fails if memory/noop selected; bus/logger must be durable.

- **A4: Durable stream replay**  
  Touch points: engines/chat/service/transport_layer.py; sse_transport.py; ws_transport.py; new durable timeline store.  
  Acceptance: pytest tests/logs/test_stream_replay.py demonstrating resume after restart (no in-memory replay).

- **A5: Audit append-only with hash chaining**  
  Touch points: engines/logging/audit.py + chosen sink; possibly nexus backends.  
  Acceptance: pytest tests/logs/test_audit_hash_chain.py (prev_hash/hash continuity; mutation fails).

- **A6: Raw storage metadata durability & mode path**  
  Touch points: engines/nexus/raw_storage/repository.py (replace env with mode, persist metadata).  
  Acceptance: pytest tests/storage/test_raw_storage_metadata.py verifying mode-scoped key and metadata persistence.

## Lane B — PII/Observability/Replay/Memory
- **B1: PII pre-call boundary**  
  Touch points: engines/chat/service/llm_client.py; engines/nexus/vector_explorer/service.py; ingest_service.py; shared redaction hook; logging/events/engine.py integration.  
  Acceptance: pytest tests/logs/test_pii_gate.py (raw prompts never exit; pii_flags logged; rehydration hook present).

- **B2: Full-scope correlation (mode+project+run/step)**  
  Touch points: all emitters (chat pipeline, vector explorer, budget usage, memory ops); StreamEvent mapping.  
  Acceptance: pytest tests/logs/test_correlation_propagation.py.

- **B3: Memory durability + scoping**  
  Touch points: engines/memory/repository.py/service.py; engines/nexus/memory/routes.py/service.py; ensure tenant/mode/project/user/session persisted durably.  
  Acceptance: pytest tests/memory/test_memory_persistence.py with durable backend only.

- **B4: Usage/cost events completeness**  
  Touch points: engines/budget/routes.py; engines/budget/repository.py; vector_explorer usage emitters.  
  Acceptance: pytest tests/logs/test_usage_events.py (run_id/step_id/model/tool, storage_class=cost, durable).

- **B5: HAZE/vector explorer compliance**  
  Touch points: engines/nexus/vector_explorer/service.py; ingest_service.py; repository.py; vector_store.py.  
  Acceptance: pytest tests/vector_explorer/test_contract_mode.py covering mode header, full envelope, durable logger, PII pre-call.
