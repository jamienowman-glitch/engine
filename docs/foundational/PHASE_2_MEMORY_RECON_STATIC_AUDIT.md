# Phase 2 Memory — Static Recon (repo-only, no tests run)

## Scoreboard
- Nexus/vector memory: PARTIAL — Vector explorer ingest/query persists corpus in Firestore and vectors in Vertex; logging defaults to no-op and lacks full context (engines/nexus/vector_explorer/service.py:33-175; ingest_service.py:32-247; repository.py:71-127; vector_store.py:63-226).
- Structured/tabular memory: FAIL — No tabular/BigQuery-style structured state beyond usage/cost summaries; nothing for general structured memory (NOT FOUND).
- Raw media storage: PARTIAL — S3 raw storage presign with enforced tenant/env prefix; metadata persistence noop; media_v2 relies on buckets (engines/nexus/raw_storage/repository.py:35-123; engines/storage/gcs_client.py:17-75).
- Session autosave/canvas state: FAIL — No autosave/canvas/session state outside memory blackboards; nexus/memory is in-memory only (engines/nexus/memory/service.py:16-72).
- Chat memory persistence: PARTIAL — Chat pipeline writes snippets to Nexus backend (firestore/bigquery) but chat bus state is in-memory/redis only (engines/chat/pipeline.py:45-69; engines/chat/service/transport_layer.py:11-121).
- Realtime replay durability: FAIL — SSE/WS replay from in-memory bus; no durable stream history (engines/chat/service/sse_transport.py:23-68; ws_transport.py:136-205; transport_layer.py:65-121).
- Routing/provider switchability: PARTIAL — Selecta/resolver used for Vertex vector store; memory/raw_storage/env-selectors exist but many default to in-memory; routing registry not applied (engines/nexus/vector_explorer/vector_store.py:63-226; engines/memory/repository.py:104-111; engines/config/runtime_config.py:60-150).
- Tenancy scoping completeness: PARTIAL — RequestContext requires tenant/env/project/app/surface (engines/common/identity.py:22-151) but many memory/logging events omit project/app/user/request/trace/run/step (e.g., engines/nexus/vector_explorer/service.py:72-104; ingest_service.py:75-201).
- PII boundary readiness: PARTIAL — Logging engine masks PII (engines/logging/events/engine.py:17-46) but vector ingest/query send raw text to embeddings and log without redaction (engines/nexus/vector_explorer/service.py:107-135; ingest_service.py:168-188); chat llm_client sends raw prompts (engines/chat/service/llm_client.py:27-50).

## What exists already (plain facts)
- Vector explorer (Haze): routes `/vector-explorer/scene` and `/vector-explorer/ingest` with tenant membership + StrategyLock; persists corpus to Firestore, vectors via Vertex Matching Engine, embeddings via Vertex, binaries to GCS; emits DatasetEvents for query/scene/ingest but logger defaults to no-op and events lack Phase 1 envelope fields (engines/nexus/vector_explorer/routes.py:32-61; ingest_routes.py:26-73; service.py:33-175; ingest_service.py:32-247; repository.py:71-127; vector_store.py:63-226).
- Memory service (legacy blackboard/session): `/memory` router enforces tenant membership; repo switch by MEMOry_BACKEND with default InMemory, optional Firestore; stores session messages and blackboards per tenant/env/user/session; no logging beyond repo ops (engines/memory/routes.py:12-65; service.py:10-53; repository.py:20-111).
- Nexus memory (session turns): `/nexus/memory/session/{id}` routes with tenant enforcement and gates; service stores turns in process-level dict `_GLOBAL_MEMORY`, logs via EventLogEntry→DatasetEvent pipeline (no sink) (engines/nexus/memory/routes.py:13-59; service.py:16-72).
- Raw storage: S3 presign with enforced tenant/env key format; fails if RAW_BUCKET missing; metadata persistence is noop; in-memory test repo exists (engines/nexus/raw_storage/repository.py:35-123).
- Chat runtime: messages persisted to Nexus via `get_backend()` and DatasetEvent logging; transport bus is in-memory unless Redis; SSE/WS replay uses bus memory only (engines/chat/pipeline.py:45-69; engines/nexus/backends/__init__.py:8-32; engines/chat/service/transport_layer.py:11-121; sse_transport.py:23-68; ws_transport.py:136-205).
- PII layer: regex mask + train_ok in logging engine before Nexus persistence; privacy prefs service with in-memory default and Firestore optional (engines/logging/events/engine.py:17-46; engines/guardrails/pii_text/engine.py:1-43; engines/privacy/train_prefs.py:117-140).
- Routing/provided configs: Selecta used for vector store config (engines/nexus/vector_explorer/vector_store.py:63-226); memory/backends/raw storage/budget all use env selectors with in-memory fallbacks (engines/memory/repository.py:104-111; engines/nexus/raw_storage/repository.py:35-123; engines/budget/repository.py:175-182).

## What is missing / unsafe / not tenant-aware
- No durable stream replay; realtime relies on in-memory bus → Phase 1/2 streaming/replay gates will fail.
- Memory repos default to in-memory and allow silent fallback; nexus/memory uses global dict with no persistence or routing.
- Event emissions in memory/vector explorer lack project/app/run/step/request/trace/severity/schema_version/storage_class.
- PII not stripped before embeddings/tool calls (vector ingest/query, chat llm_client).
- Structured/tabular memory absent; no autosave/canvas/workspace state; no DSAR/retention hooks for memory.
- Audit trail for memory operations absent; vector ingest audit uses dataset events without hash chain or full context.

## Do-not-break contracts (fragile/currently relied upon)
- Raw storage key format enforces `tenants/{tenant}/{env}/raw/...`; raising if RAW_BUCKET missing (engines/nexus/raw_storage/repository.py:35-102).
- Vector explorer expects Vertex configs via selecta/runtime_config; failures raise VectorStoreConfigError (vector_store.py:63-172,218-226).
- Memory session routes require user_id; RequestContext enforcement returns 400 if missing (engines/memory/service.py:15-28).
- StrategyLock required on vector ingest (ingest_routes.py:38-40).

## Evidence index
- RequestContext scope keys: engines/common/identity.py:22-151.
- Vector explorer routes: engines/nexus/vector_explorer/routes.py:32-61; ingest_routes.py:26-73.
- Vector explorer service events/logging gaps: engines/nexus/vector_explorer/service.py:72-104,107-135,167-175.
- Vector ingest event/audit/usage: engines/nexus/vector_explorer/ingest_service.py:75-201,160-165,228-246.
- Corpus repo persistence: engines/nexus/vector_explorer/repository.py:71-127 (Firestore) + 33-69 (InMemory).
- Vector store backend/routing: engines/nexus/vector_explorer/vector_store.py:63-226.
- Memory router/service/repo and env fallback: engines/memory/routes.py:12-65; service.py:10-53; repository.py:20-111,104-111.
- Nexus memory routes/service (in-memory global): engines/nexus/memory/routes.py:13-59; service.py:16-72.
- Raw storage S3 repo: engines/nexus/raw_storage/repository.py:35-123.
- Chat logging + Nexus backend: engines/chat/pipeline.py:45-69; engines/nexus/backends/__init__.py:8-32.
- Realtime replay in-memory: engines/chat/service/transport_layer.py:65-121; sse_transport.py:23-68; ws_transport.py:136-205.
- PII mask layer: engines/logging/events/engine.py:17-46; engines/guardrails/pii_text/engine.py:1-43; privacy prefs fallback: engines/privacy/train_prefs.py:117-140.
- LLM/tool calls without redaction: engines/chat/service/llm_client.py:27-50; engines/nexus/vector_explorer/service.py:107-135; ingest_service.py:168-188.

## Commands run (static only)
- `rg -n "HAZE|haze|explorer|3d|embedding explorer|vector explorer|nexus explorer" engines docs | head -n 300`
- `nl -ba engines/nexus/vector_explorer/routes.py | sed -n '1,200p'`
- `nl -ba engines/nexus/vector_explorer/ingest_routes.py | sed -n '1,200p'`
- `nl -ba engines/nexus/vector_explorer/service.py | sed -n '1,240p'`
- `nl -ba engines/nexus/vector_explorer/ingest_service.py | sed -n '1,260p'`
- `nl -ba engines/nexus/vector_explorer/repository.py | sed -n '1,220p'`
- `nl -ba engines/nexus/vector_explorer/vector_store.py | sed -n '1,240p'`
- `nl -ba engines/nexus/vector_explorer/schemas.py | sed -n '1,240p'`
- `nl -ba engines/memory/routes.py | sed -n '1,200p'`
- `nl -ba engines/memory/service.py | sed -n '1,240p'`
- `nl -ba engines/memory/repository.py | sed -n '1,220p'`
- `nl -ba engines/nexus/memory/routes.py | sed -n '1,240p'`
- `nl -ba engines/nexus/memory/service.py | sed -n '1,120p'`
- `nl -ba engines/nexus/raw_storage/repository.py | sed -n '1,200p'`
