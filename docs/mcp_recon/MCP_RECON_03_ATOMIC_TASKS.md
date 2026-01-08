## Section A — MCP Gateway (engines lane)
- MCP-ENG-01 — Type: INTEGRATION. Preconditions: `engines/common/identity.py`, `engines/common/error_envelope.py` available. Files/locations: `engines/mcp_gateway/server.py`, `engines/mcp_gateway/__init__.py`. Acceptance: FastAPI app boots with shared `register_error_handlers` wired; health route returns version and uses `RequestContextBuilder` for header parsing. Unblocks: later tool/list + call wiring.
- MCP-ENG-02 — Type: DX. Preconditions: MCP-ENG-01. Files: `engines/mcp_gateway/inventory.py`. Acceptance: `/tools/list` (or JSON-RPC equivalent) returns inventory derived from mounted routers in `engines/chat/service/server.py:70` (names, routes, request models where available) with lane metadata; includes chat_service and media_v2 entries. Unblocks: tool schema publication.
- MCP-ENG-03 — Type: INTEGRATION. Preconditions: MCP-ENG-01. Files: `engines/mcp_gateway/tools/chat.py`. Acceptance: `tools.call` for `chat_service.append_message` executes in-process (imports `engines/chat/service/routes.append_message` and publishes via `publish_message`) returning `ChatMessageOut`; preserves `RequestContext` from MCP identity headers. Unblocks: first real MCP tool.
- MCP-ENG-04 — Type: INTEGRATION. Preconditions: MCP-ENG-01. Files: `engines/mcp_gateway/tools/media_v2.py`. Acceptance: `tools.call` for `media_v2.create_media_asset` supports JSON body path (no multipart) and returns `MediaAsset`; registers artifact via `MediaService.register_remote`; identity enforced via `require_tenant_membership`. Unblocks: artifact-producing tool path.
- MCP-ENG-05 — Type: QUALITY. Preconditions: MCP-ENG-01. Files: `engines/mcp_gateway/errors.py`. Acceptance: shared mapper wraps exceptions into `ErrorEnvelope` and sets JSON-RPC `error.data` to `ErrorEnvelope.model_dump()`; validated by unit tests covering HTTPException and validation errors. Unblocks: consistent MCP error contract.
- MCP-ENG-06 — Type: QUALITY. Preconditions: MCP-ENG-02/03/04. Files: `engines/mcp_gateway/tests/test_tools.py`. Acceptance: Tests cover `tools/list` inventory completeness, chat_service tool call happy/invalid path, media_v2 tool call happy/missing mode header; asserts error mapping mirrors `ErrorEnvelope.http_status`. Unblocks: deploy confidence.

## Section B — Prod-lite readiness (per engine)
### chat_service
- PL-CHAT-01 — Type: QUALITY. Preconditions: chat_store configured. Files: `engines/chat/service/transport_layer.py`, `engines/chat/store_service.py`. Acceptance: durable replay backed by persisted timeline (not just bus) with cursor validation; SSE/WS tests prove resume after process restart. Unblocks: MCP streaming reliability.
- PL-CHAT-02 — Type: SECURITY. Files: `engines/chat/service/sse_transport.py`, `engines/chat/service/ws_transport.py`. Acceptance: enforce `X-Mode/X-Project-Id` in `_sse_context`/WS hello using `assert_context_matches`; tests reject missing/override headers. Unblocks: identity parity for MCP streams.
- PL-CHAT-03 — Type: QUALITY. Files: `engines/chat/service/http_transport.py`. Acceptance: ensure `_http_exception_handler` wraps all HTTPException paths; add tests for validation + gate_chain rejection returning canonical `ErrorEnvelope`. Unblocks: MCP error passthrough.

### canvas_stream
- PL-CANVAS-01 — Type: INTEGRATION. Files: `engines/canvas_stream/router.py`, `engines/canvas_stream/service.py`. Acceptance: add durable timeline store (media_v2 or object store) for canvas events and replay with Last-Event-ID; tests simulate restart + resume. Unblocks: streaming tool stability.
- PL-CANVAS-02 — Type: SECURITY. Files: `engines/canvas_stream/router.py`. Acceptance: enforce `X-Mode/X-Project-Id/X-App-Id` and emit `ErrorEnvelope` on mismatch; add tests for missing headers and ticket misuse. Unblocks: MCP identity contract.

### media_v2_assets
- PL-MEDIA-01 — Type: SECURITY. Files: `engines/muscle/media_v2/service.py`. Acceptance: make S3/Firestore backends mandatory in sellable modes (fail fast instead of `LocalMediaStorage`); unit tests prove error when RAW_BUCKET missing. Unblocks: prod-safe artifact durability.
- PL-MEDIA-02 — Type: QUALITY. Files: `engines/muscle/media_v2/routes.py`, `engines/muscle/media_v2/tests`. Acceptance: add tests for multipart + JSON creation enforcing tenant/auth and rejecting cross-tenant artifact creation. Unblocks: MCP tool confidence.
- PL-MEDIA-03 — Type: DX. Files: `engines/muscle/media_v2/models.py`. Acceptance: document artifact kind → meta requirements (e.g., visual_meta, video_region_summary) and expose deterministic `pipeline_hash`/backend_version in meta; tests assert presence. Unblocks: registry metadata and determinism reporting.

### audio_service
- PL-AUDIO-01 — Type: QUALITY. Files: `engines/muscle/audio_service/service.py`. Acceptance: emit budget/audit events per operation using `BudgetService.record_usage` and `event_spine` with request_id/run_id; tests assert calls. Unblocks: observability for MCP.
- PL-AUDIO-02 — Type: QUALITY. Files: `engines/muscle/audio_service/tests`. Acceptance: add invalid-input tests (missing asset/artifact) returning canonical error; ensure RequestContext tenant/env enforced in service layer. Unblocks: safer tool exposure.

### video_render
- PL-VRENDER-01 — Type: QUALITY. Files: `engines/muscle/video_render/service.py`. Acceptance: compute deterministic `pipeline_hash` for render plan (inputs + profile) and include in artifact meta; tests cover identical plans hashing equal. Unblocks: idempotent MCP job tracking.
- PL-VRENDER-02 — Type: SECURITY. Files: `engines/muscle/video_render/routes.py`. Acceptance: enforce budget/audit emits per render/job submission with surface/project metadata; tests assert BudgetService called. Unblocks: billing readiness.
- PL-VRENDER-03 — Type: INTEGRATION. Files: `engines/muscle/video_render/routes.py`, `engines/chat/service/server.py`. Acceptance: introduce async worker hook (queue stub) or explicit “async not supported” flag surfaced in `tools.list`; documented in tests. Unblocks: correct MCP invocation type tagging.

### video_timeline
- PL-VTIMELINE-01 — Type: SECURITY. Files: `engines/muscle/video_timeline/service.py`. Acceptance: fail fast when Firestore config missing (no silent default); tests simulate missing project env -> raises. Unblocks: predictable MCP failures.
- PL-VTIMELINE-02 — Type: QUALITY. Files: `engines/muscle/video_timeline/routes.py`. Acceptance: add media_v2 linkage option for clips (asset/artifact validation) with guarded checks; tests cover rejection of unknown asset_id. Unblocks: downstream render tools consuming timeline via MCP.

### cad_ingest
- PL-CAD-01 — Type: INTEGRATION. Preconditions: routing registry ready. Files: `engines/chat/service/server.py`, `engines/muscle/cad_ingest/routes.py`. Acceptance: mount `cad_ingest_router` in create_app behind feature flag; smoke test with FastAPI TestClient proves availability. Unblocks: MCP tool exposure.
- PL-CAD-02 — Type: QUALITY. Files: `engines/muscle/cad_ingest/service.py`. Acceptance: add remote `source_uri` ingest via raw_storage presign + download path; tests cover both multipart and remote. Unblocks: MCP tool compatibility with remote files.
- PL-CAD-03 — Type: SECURITY. Files: `engines/muscle/cad_ingest/routes.py`. Acceptance: emit budget/audit events with gate_chain integration when ingesting; tests assert gate_chain invoked. Unblocks: compliance for MCP.

### vector_explorer
- PL-VECTOR-01 — Type: QUALITY. Files: `engines/nexus/vector_explorer/routes.py`, `ingest_routes.py`. Acceptance: wrap errors with `ErrorEnvelope` and enforce `RequestContext` presence (mode/project) in both query and ingest; tests cover 400/401 cases. Unblocks: MCP error/identity contract.
- PL-VECTOR-02 — Type: QUALITY. Files: `engines/nexus/vector_explorer/schemas.py`. Acceptance: add schema export helpers producing JSON schema blobs for MCP tools (query + ingest forms) with required tags/space/tenant fields; tests assert schema completeness. Unblocks: tool schema generation.

### budget_usage
- PL-BUDGET-01 — Type: QUALITY. Files: `engines/budget/repository.py`. Acceptance: add durable backend option (e.g., Firestore/S3) with configuration guard; tests verify write/read in durable mode. Unblocks: MCP usage reporting resilience.
- PL-BUDGET-02 — Type: QUALITY. Files: `engines/budget/routes.py`, `engines/budget/tests`. Acceptance: add validation for missing mode/project/app and return `ErrorEnvelope` using common helper; tests assert 400 with canonical structure. Unblocks: consistent MCP error handling.

## Section C — Registry plan (Specs Registry fixtures)
- REG-01 — Type: PLAN. Preconditions: MCP-ENG-02 inventory. Files: `docs/mcp_recon/MCP_RECON_00_ENGINE_INDEX.tsv`, `northstar-engines/docs/WORK_ENG-1_REGISTRY_SPECS.md` (reference). Acceptance: draft Spec Registry component JSON fixtures (kind=component, metadata.spec_class=muscle) for at least chat_service and media_v2 including invocation type and schema refs; stored under `docs/mcp_recon/fixtures/` (no runtime wiring). Unblocks: future registry sync.
- REG-02 — Type: DX. Preconditions: REG-01. Files: `engines/registry/service.py` (planned). Acceptance: outline adapter contract (no code) describing how inventory feeds Specs Registry: fields for `engine_id`, `lane`, `invocation_types`, schema pointer; documented in Markdown in `docs/mcp_recon/REGISTRY_PLAN.md`. Unblocks: later MCP discovery.
- REG-03 — Type: QUALITY. Preconditions: REG-01. Files: `docs/mcp_recon/MCP_RECON_00_ENGINE_INDEX.tsv`. Acceptance: add unit test fixture (YAML/JSON) verifying TSV rows convert to registry-ready dicts (engine_id, name, schema_uri) without hitting network; stored under `docs/mcp_recon/fixtures/test_inventory.json`. Unblocks: future automation for registry publishing.
