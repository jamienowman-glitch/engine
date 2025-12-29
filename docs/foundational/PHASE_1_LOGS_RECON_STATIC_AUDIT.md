# Phase 1 Logs Recon — Static Audit (no tests run)

## 0) Executive summary
- Logging spine today is the DatasetEvent pipeline with PII masking and Nexus persistence (engines/logging/events/engine.py:1-47; engines/dataset/events/schemas.py:9-32). Audit helpers wrap it for sensitive actions (engines/logging/audit.py:18-53) and generic EventLog mapping exists (engines/logging/event_log.py:35-75).
- Events are stored via Nexus backends (Firestore/BigQuery) and echoed to stdout (engines/nexus/backends/__init__.py:8-33; engines/nexus/backends/firestore_backend.py:68-71; engines/nexus/backends/bigquery_backend.py:10-36; engines/logging/events/engine.py:37-46).
- Cost/usage tracking exists via budget usage events and repos (engines/budget/routes.py:12-78; engines/budget/service.py:19-43; engines/budget/repository.py:36-182) plus analytics/marketing telemetry routes (engines/analytics_events/service.py:22-105).
- Correlation context is carried in RequestContext (request_id/tenant/env/project/user) and reused across realtime envelopes (engines/common/identity.py:22-151; engines/realtime/contracts.py:44-91; engines/chat/service/sse_transport.py:23-68; engines/chat/service/ws_transport.py:137-205).
- Missing for audit-grade: no immutable/auditable ledger, analytics and privacy prefs default to in-memory, tool-call logs store raw prompts without redaction, no shared “pulse” or agent timeline, and SSE/WS rely on in-memory bus without durable replay.

## 1) Inventory map
| Capability | Exists? | Where (path:lines) | Notes |
| --- | --- | --- | --- |
| Developer logs (stdout/logger) | PARTIAL | engines/logging/events/engine.py:37-46; engines/chat/service/ws_transport.py:136-205 | Dataset events emit JSON to stdout; ad-hoc logger warnings on WS mismatches, no centralized formatter/config. |
| Correlation/trace IDs | PARTIAL | engines/common/identity.py:22-151; engines/realtime/contracts.py:44-91; engines/dataset/events/schemas.py:28-32 | request_id generated and carried; StreamEvent has event_id/trace_id/span_id; no system-wide trace propagation beyond chat/realtime. |
| Agent/flow timeline events | PARTIAL | engines/chat/pipeline.py:55-68; engines/logging/event_log.py:35-75 | Chat messages logged as DatasetEvents; generic EventLogEntry→DatasetEvent adapter exists; no broader agent step timeline. |
| Shared state snapshot / pulse | NO | NOT FOUND (rg for “pulse|heartbeat” shows only WS keepalive at engines/chat/service/ws_transport.py:128-135) | No persisted heartbeat or state snapshot events. |
| Attribution (actor/tool/model) | PARTIAL | engines/logging/audit.py:26-49; engines/dataset/events/schemas.py:13-32; engines/realtime/contracts.py:19-38; engines/nexus/logging.py:18-30 | Dataset/Audit events include agentId/actorType; StreamEvent routing carries actor; ModelCallLog tracks model_id; not enforced everywhere. |
| Tool-call capture/logging | PARTIAL | engines/nexus/rag_service.py:38-111; engines/eval/service.py:73-87; engines/nexus/logging.py:18-30 | ModelCallLog records prompts/model/outputs; no redaction and no storage backend wired. |
| Streaming event channels | YES (non-durable) | engines/chat/service/sse_transport.py:23-68; engines/chat/service/ws_transport.py:136-205; engines/realtime/contracts.py:74-165; engines/chat/service/transport_layer.py:65-121 | SSE uses Last-Event-ID for replay from in-memory bus; WS supports resume cursor; StreamEvent carries event_id/meta but bus is in-memory unless Redis configured. |
| Audit events | PARTIAL | engines/logging/audit.py:18-53 | Emits DatasetEvent with action/actor; relies on logging engine; no immutable store or review workflow. |
| Safety-route logging | PARTIAL | engines/analytics_events/service.py:38-71 (gate chain best-effort); engines/control/temperature/service.py:28-42 | Some gates wrap telemetry; no dedicated safety/audit logs for kill-switch/strategy_lock actions. |
| Cost/usage accounting | YES (scoped) | engines/budget/routes.py:12-78; engines/budget/service.py:19-43; engines/budget/repository.py:36-182 | Records per-tenant/provider/model usage with costs; persistence is Firestore or in-memory fallback. |
| PII filtering/redaction | PARTIAL | engines/logging/events/engine.py:17-46; engines/guardrails/pii_text/engine.py:1-43; engines/privacy/train_prefs.py:117-140 | PII regex mask + train_ok before logging; LLM/tool calls (llm_client, rag_service, eval) do not redact before sending/storing prompts. |
| Retention/export controls | NO | NOT FOUND; closest is training prefs opt-out (engines/privacy/train_prefs.py:117-140) | No retention periods, DSAR export/delete, or tenant-level log retention. |
| Schema/versioning | PARTIAL | engines/realtime/contracts.py:74-91; engines/dataset/events/schemas.py:9-32 | StreamEvent has v and meta.schema_ver; DatasetEvent lacks schema version or migration strategy. |
| Audit immutability/WORM | NO | engines/nexus/backends/firestore_backend.py:68-71; engines/nexus/backends/bigquery_backend.py:26-35 | Events are plain writes; no append-only proofs, signatures, or tamper detection. |

## 2) Event model reality check
- Canonical schema: DatasetEvent with tenantId/env/surface/agentId/input/output/metadata/traceId/requestId (engines/dataset/events/schemas.py:9-32).
- Event processing: logging engine strips PII, sets train_ok from privacy prefs, writes to Nexus backend (engines/logging/events/engine.py:17-46).
- Backend selection: get_backend enforces firestore|bigquery only; memory/noop raise (engines/nexus/backends/__init__.py:8-32). Firestore adds to `nexus_events` collection (engines/nexus/backends/firestore_backend.py:68-71); BigQuery adds ingested_at and inserts rows (engines/nexus/backends/bigquery_backend.py:26-35).
- Separation: no distinct audit ledger vs behavior timeline vs ops logs; all DatasetEvents share one pipeline; model call logs are separate ad-hoc dataclasses without storage (engines/nexus/logging.py:18-30).

## 3) Tenant/user/project/surface/app context coverage
- RequestContext requires tenant_id/env/project_id and fills surface/app defaults, generating request_id (engines/common/identity.py:22-151). assert_context_matches enforces tenant/env/project/surface/app (engines/common/identity.py:154-177).
- DatasetEvent carries tenantId/env/agentId/traceId/requestId but lacks project/app/surface fields beyond free-form surface string (engines/dataset/events/schemas.py:9-32).
- Chat pipeline logs events with tenant/env/request_id but no project/surface/app from context (engines/chat/pipeline.py:55-68). SSE/WS enforce tenant membership and propagate request_id into StreamEvent meta but do not attach project/app (engines/chat/service/sse_transport.py:23-68; engines/chat/service/ws_transport.py:136-205; engines/realtime/contracts.py:19-90).
- Analytics events use RequestContext tenant/env/user but not project/surface defaults beyond provided surface (engines/analytics_events/service.py:38-95).

## 4) Streams and UI readiness
- SSE endpoint `/sse/chat/{thread_id}` uses Last-Event-ID header to replay from in-memory bus and wraps messages into StreamEvent with event_id/type (engines/chat/service/sse_transport.py:23-68; engines/chat/service/transport_layer.py:100-118).
- WS endpoint `/ws/chat/{thread_id}` accepts last_event_id query, replays missed messages, and emits resume_cursor/presence events with event_id/meta.persist fields (engines/chat/service/ws_transport.py:136-205).
- StreamEvent envelope defines v/event_id/seq/trace_id/routing/meta.persist (engines/realtime/contracts.py:74-165), but no durable store or ordering guarantees beyond in-memory/Redis bus.

## 5) PII boundary inventory
- Logging pipeline masks email/phone/card/postal and sets train_ok before persisting (engines/logging/events/engine.py:17-46; engines/guardrails/pii_text/engine.py:1-43) and honors tenant/user opt-out (engines/privacy/train_prefs.py:117-140).
- Chat LLM calls send raw prompts/history to Vertex with no redaction (engines/chat/service/llm_client.py:27-50).
- RAG/Eval tool-call logging stores raw prompt text in ModelCallLog without masking or persistence backend (engines/nexus/rag_service.py:38-95; engines/eval/service.py:73-87; engines/nexus/logging.py:18-30).
- Budget/usage and analytics events store user-provided metadata without PII stripping (engines/budget/routes.py:12-78; engines/analytics_events/service.py:38-95).

## 6) Delta to Phase 1 Logs DoD
- No immutable/audit-grade ledger; DatasetEvents are simple Firestore/BQ writes with no signing or append-only proof (engines/nexus/backends/firestore_backend.py:68-71; engines/nexus/backends/bigquery_backend.py:26-35).
- Chat/analytics pipelines omit project/app/surface context in logged events, so correlation across control-plane objects is incomplete (engines/chat/pipeline.py:55-68; engines/analytics_events/service.py:38-95).
- Tool-call/model-call logging captures raw prompts without PII filtering or storage backend (engines/nexus/rag_service.py:38-95; engines/eval/service.py:73-87; engines/nexus/logging.py:18-30).
- Telemetry repos default to in-memory (analytics events, budget usage, privacy prefs) risking silent loss and no cross-tenant durability (engines/analytics_events/service.py:22-36; engines/budget/repository.py:175-182; engines/privacy/train_prefs.py:117-124).
- No shared state snapshot/pulse or agent timeline beyond chat message events (NOT FOUND; only WS heartbeat at engines/chat/service/ws_transport.py:128-135).
- SSE/WS replay relies on in-memory bus; no durable stream history or ordering guarantees (engines/chat/service/transport_layer.py:65-121).
- PII stripping applies only to DatasetEvent logging; LLM/embedding calls and ModelCallLog capture go out unredacted (engines/chat/service/llm_client.py:27-50; engines/nexus/rag_service.py:38-95).
- No retention/export/DSAR or tenant-level log retention controls (NOT FOUND; closest opt-out is engines/privacy/train_prefs.py:117-140).

## 7) Repo artifacts created
- Written: docs/foundational/PHASE_1_LOGS_RECON_STATIC_AUDIT.md
- git status (this file only): see current working tree output below.
