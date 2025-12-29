# Phase 1 Logs — HAZE / Nexus Explorer Static Recon (no tests run)

## 1) Code & routes (Haze explorer)
- HTTP scene query: `engines/nexus/vector_explorer/routes.py:32-61` mounts `GET /vector-explorer/scene` with RequestContext + require_tenant_membership; service wired to Firestore corpus + Vertex vector store + Vertex embeddings (lines 21-29). Mounted in app factory at `engines/chat/service/server.py:71-119` (includes `vector_explorer_router` and `vector_ingest_router`).
- HTTP ingest: `engines/nexus/vector_explorer/ingest_routes.py:26-73` exposes `POST /vector-explorer/ingest` with RequestContext + membership + StrategyLock gate.
- Scene builder (3D/scene mapping): `engines/nexus/vector_explorer/scene_builder.py:12-48` builds `Scene` using `Recipe.vector_space_explorer` from scene_engine.
- Vector explorer service: `engines/nexus/vector_explorer/service.py:33-175` handles queries, scene build, and usage logging.
- Ingest service: `engines/nexus/vector_explorer/ingest_service.py:32-247` handles uploads/embeddings/corpus writes/audit.

## 2) Data sources & persistence
- Corpus metadata: Firestore via `FirestoreVectorCorpusRepository` (engines/nexus/vector_explorer/repository.py:71-127) requiring GCP project; in-memory repo exists for tests (lines 33-69).
- Vector store: Vertex Matching Engine adapter `VertexExplorerVectorStore` (engines/nexus/vector_explorer/vector_store.py:63-226) using selecta/runtime_config for project/endpoint/index; raises VectorStoreConfigError if missing; `query_by_datapoint_id` is NotImplemented (line 205).
- Embeddings: VertexEmbeddingAdapter default (routes/service/ingest constructors).
- Binary storage: GCS via `GcsClient` (engines/storage/gcs_client.py:17-75) requiring RAW_BUCKET/DATASETS_BUCKET; local temp fallback only when bucket name starts with `test-` (lines 36-52).
- Event logging: service logger defaults to no-op (`_dataset_event_logger` returns None at engines/nexus/vector_explorer/service.py:167-175); ingest service event_logger defaults to `lambda e: None` (engines/nexus/vector_explorer/ingest_service.py:32-47) so DatasetEvents drop unless injected.

## 3) Event/logging inventory (what is emitted today)
- Query events: DatasetEvent with tenantId/env/surface/input/output/metadata.kind `vector_explorer.query` (engines/nexus/vector_explorer/service.py:72-88); no project/app/run/step/request_id/schema_version/severity.
- Scene compose events: DatasetEvent metadata.kind `vector_explorer.scene_composed` (engines/nexus/vector_explorer/service.py:94-104); same field gaps.
- Ingest attempt/success/fail events: DatasetEvent kinds `vector_ingest.attempt|success|fail` (engines/nexus/vector_explorer/ingest_service.py:75-159,190-201); no project/app/run/step/request_id/schema_version/severity; defaults to surface `vector_ingest`.
- Audit: `emit_audit_event` called with RequestContext(request_id="vector_ingest", tenant_id, env, user_id) and metadata asset_id/space (engines/nexus/vector_explorer/ingest_service.py:160-165); uses DatasetEvent via audit helper but still lacks project/app/run/step.
- Cost/usage: Budget UsageEvent recorded for embeddings (engines/nexus/vector_explorer/service.py:118-135; ingest_service.py:228-246) with surface `vector_explorer` or `vector_ingest`, tool_type embedding, provider vertex; no run_id/step_id/schema_version.
- Model/tool call logging: none; ModelCallLog not used here.
- Streaming: no SSE/WS hooks in explorer; only HTTP.

## 4) Context coverage vs canonical keys
- Present: tenant_id/env on all DatasetEvents (service:72-88,94-104; ingest:77-158,192-199). RequestContext includes project_id/surface/app, but those are not attached to emitted events.
- Missing on events: project_id, surface_id (only freeform `surface` string), app_id, user_id (agentId fixed to vector_explorer/vector_ingest), request_id, trace_id (except optional trace_id in query input), run_id, step_id, severity, schema_version, storage_class.
- RequestContext usage: ingest routes/services create RequestContext with tenant/env (project_id defaults to "p_internal") before usage logging (ingest_service.py:125-133,176-188); VectorService builds RequestContext only when embedding text (service.py:107-118) with no project/app/user set.
- Audit call includes user_id if provided (ingest_service.py:160-165) but still lacks project/app/run/step.

## 5) Minimum deltas to align with Phase 1 envelopes/event types
- Attach full canonical envelope fields (tenant/env/project/surface/app/user/request_id/trace_id/run_id/step_id/severity/schema_version/storage_class) to DatasetEvents and audit events in service.py:72-104 and ingest_service.py:75-201,160-165.
- Replace no-op event loggers with canonical writer; fail fast if sinks unavailable (align with Lane A A2/A3).
- Emit tool_call_* events around embedding/vector store calls with redacted inputs; add state_pulse/flow_step if explorer participates in flows.
- Add PII redaction before embeddings and before logging text_content/query_text; currently raw text passes to Vertex and logs (service.py:107-135; ingest_service.py:168-188).
- Ensure cost/usage events carry run_id/step_id/model_id/tool_id per Phase 1 event types; add schema_version/severity.
- Add durable store for replay if explorer events are streamed later; today there is no stream but Phase 1 streaming gate would need durable timeline alignment.

## 6) Risks when Phase 1 enforcement turns on
- Missing required envelope fields will fail contract/acceptance (events in service.py and ingest_service.py lack project/app/run/step/request/trace/severity/schema_version).
- Event logger default no-op means audit/ops sinks would see nothing; Phase 1 “no silent drop” will fail startup or tests.
- Raw text_content/query_text sent to embeddings/logs without redaction → PII gate failure (service.py:107-135; ingest_service.py:168-188).
- Vector store requires Vertex config; if routing registry enforces “no in-memory”, current selecta-based init must be validated to avoid startup failure (vector_store.py:81-226).
- Query-by-id not implemented; streaming/replay absent; any Phase 1 durable replay gate would fail without timeline store for explorer events.
