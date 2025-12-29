# Phase 1 Logs — TODO by Lane (implementation-ready, no code changes yet)

## Lane A — Logging Spine + Storage
- **A1: Canonical envelope upgrade (schema + adapters)**  
  Evidence: DatasetEvent lacks project_id/app_id/run_id/step_id/severity/schema_version (engines/dataset/events/schemas.py:9-32); StreamEvent routing omits project_id/app_id defaults (engines/realtime/contracts.py:19-165).  
  Work: Add schema fields + enums; provide adapters mapping StreamEvent/Audit/EventLog→canonical; forbid emitting events missing tenant/env/project/surface/app.  
  Verify: `python -m pytest tests/logs/test_event_contract.py` (contract validates required fields and rejects missing scope).

- **A2: Dual sinks (ops vs audit) with no in-memory fallback**  
  Evidence: Nexus backends are ops-only, plain Firestore/BQ writes (engines/nexus/backends/__init__.py:8-32; firestore_backend.py:68-71; bigquery_backend.py:10-36).  
  Work: Define ops_timeline store + audit store interfaces; implement startup validation to fail if only in-memory/noop; wire canonical writer to both where storage_class requires.  
  Verify: `python -m pytest tests/logs/test_sink_selection.py` (fails when backend missing; passes when ops+audit configured).

- **A3: Audit immutability (hash chaining)**  
  Evidence: No prev_hash/hash fields in audit path (same files as A2).  
  Work: Add hash chaining fields + append-only audit write path; verify hash chain per tenant/run.  
  Verify: `python -m pytest tests/logs/test_audit_hash_chain.py`.

- **A4: PII redaction extension to tool/model calls**  
  Evidence: LLM/tool calls send raw prompts (engines/chat/service/llm_client.py:27-50; engines/nexus/rag_service.py:38-96; engines/eval/service.py:73-87). Logging engine already masks (engines/logging/events/engine.py:17-46).  
  Work: Route all tool/model call inputs/outputs through shared redaction layer before emit/call; document optional encrypted payload stub.  
  Verify: `python -m pytest tests/logs/test_pii_gate.py` (assert redacted payload stored/emitted).

- **A5: Cost/usage plumbing with canonical events**  
  Evidence: Budget usage events lack run_id/step_id/schema_version (engines/budget/routes.py:12-78; engines/budget/repository.py:36-182).  
  Work: Emit usage_recorded events with required fields; ensure storage_class=cost hits durable sink; enforce no in-memory repo in prod path.  
  Verify: `python -m pytest tests/logs/test_usage_events.py`.

- **A6: Retention/export/DSAR scaffolding**  
  Evidence: None (NOT FOUND; only training prefs opt-out engines/privacy/train_prefs.py:117-140).  
  Work: Define retention policy model per tenant/app; add CLI/API stubs for export run/tenant slice and delete-with-audit; no silent no-op.  
  Verify: `python -m pytest tests/logs/test_retention_export.py`.

- **A7: Structured developer logs with correlation**  
  Evidence: Only stdout JSON from logging engine; no standard logger (engines/logging/events/engine.py:37-46).  
  Work: Introduce logging middleware/handler injecting request_id/trace_id/tenant/project; tie exception logs to event_id.  
  Verify: `python -m pytest tests/logs/test_structured_logging.py`.

## Lane B — Flow/Agent Observability + Streaming
- **B1: Flow/step timeline emission (“story mode”)**  
  Evidence: Chat emits agent_message only (engines/chat/pipeline.py:55-126); no flow_started/step_started.  
  Work: Define event_type enum + emit flow_started/ended, step_started/ended, agent_decision; include run_id/step_id.  
  Verify: `python -m pytest tests/logs/test_flow_timeline.py`.

- **B2: State pulse events (shared state snapshot)**  
  Evidence: None (NOT FOUND; only WS heartbeat engines/chat/service/ws_transport.py:128-135).  
  Work: Add state_pulse event spec with key diffs/hash; emit hook from orchestrator layer; route to ops store.  
  Verify: `python -m pytest tests/logs/test_state_pulse.py`.

- **B3: Tool/model call accountability events**  
  Evidence: ModelCallLog dataclass only, no events/sinks (engines/nexus/logging.py:18-30; engines/nexus/rag_service.py:38-111; engines/eval/service.py:73-87).  
  Work: Emit tool_call_started/ended/failed events with provider/model ids, redacted payloads, cost linkages; persist to ops/audit as needed.  
  Verify: `python -m pytest tests/logs/test_tool_call_events.py`.

- **B4: SSE/WS selective stream + durable replay**  
  Evidence: SSE/WS replay from in-memory bus (engines/chat/service/sse_transport.py:23-68; engines/chat/service/ws_transport.py:136-205; engines/chat/service/transport_layer.py:65-121).  
  Work: Back stream cursor by durable timeline; allow stream filters; ensure idempotent event IDs; preserve Last-Event-ID/resume_cursor semantics.  
  Verify: `python -m pytest tests/logs/test_stream_replay.py`.

- **B5: Correlation propagation across routers/services**  
  Evidence: RequestContext has project/surface/app but not attached to DatasetEvents/StreamEvents (engines/common/identity.py:22-151; engines/dataset/events/schemas.py:9-32; engines/realtime/contracts.py:19-165).  
  Work: Ensure emitted events carry tenant/env/project/surface/app/user/request_id/trace_id/run_id consistently; add middleware/assertions.  
  Verify: `python -m pytest tests/logs/test_correlation_propagation.py`.
