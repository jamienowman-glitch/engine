# BACKEND_TRUTH (Repo Scan, No Guessing)

Statuses: ✅ exists & used · ⚠️ partial/stub · ❌ missing

## RequestContext / tenant-env scoping
- Status: ⚠️
- Where: `engines/common/identity.py` (`RequestContext`, `get_request_context`, `assert_context_matches`)
- Behavior: Requires `tenant_id` + `env` (headers/query/body), optional `user_id`, `membership_role`; 400 if missing; token decode optional via `Authorization: Bearer`.
- Gaps: Routes for chat (`engines/chat/service/*`), media_v2, video_timeline, video_render do not depend on RequestContext or auth.

## Identity/Auth boundaries
- Status: ⚠️
- Where: HS256 JWT in `engines/identity/jwt_service.py`; auth dependency `engines/identity/auth.py`; routes in `engines/identity/routes_auth.py`.
- Behavior: `get_auth_context` requires bearer; falls back to Cognito verifier if configured; roles via `role_map`. Bootstrap creates user/tenant on signup; Cognito bootstrap ensures membership.
- Gaps: Many engine routes skip auth entirely; no global middleware; Tenant-0/1 not defined.

## Event logging
- Status: ✅
- Where: `engines/logging/events/engine.py` (DatasetEvent -> PII strip -> Nexus backend), schema `engines/dataset/events/schemas.py`, helper `engines/logging/event_log.py` (EventLogEntry -> DatasetEvent).
- Behavior: PII text scan + training opt-out (`engines/privacy/train_prefs.py`); writes to Nexus backend (FireStore/BigQuery/memory/noop via `engines/nexus/backends/__init__.py`); best-effort (exceptions swallowed in helper).
- Gaps: No audit detail beyond DatasetEvent metadata; no legal-grade audit chain.

## Nexus write paths
- Status: ⚠️
- Where: `engines/nexus/backends/firestore_backend.py|bigquery_backend.py|memory_backend.py|noop_backend.py`; chat pipeline writes snippets via `engines/chat/pipeline.py`.
- Behavior: DatasetEvents and snippets persist through backend abstraction; search/index/cards/packs/settings routes exist but some routers are incomplete (e.g., `nexus/raw_storage/routes.py`, `nexus/atoms/routes.py`, `nexus/packs/routes.py` have missing deps/types).
- Gaps: No canonical canvas/collab schema; some Nexus routers fail at import/runtime; no revision log model.
- Update: PHASE_02 enforces RequestContext + AuthContext on raw_storage/atoms/packs/cards/index/settings/runs/memory routes via `engines/nexus/hardening/auth.py`, preventing missing/ cross-tenant tokens from calling control-plane APIs.

## Streaming (SSE/WS)
- Status: ⚠️
- Where: WebSocket `engines/chat/service/ws_transport.py`; SSE `engines/chat/service/sse_transport.py`; mounted via `engines/chat/service/server.py`.
- Behavior: In-memory bus per `thread_id`; WS accepts/echoes messages, no auth/tenant, no heartbeat/reconnect or cursor; SSE streams `event: message` with no Last-Event-ID handling.
- Gaps: No routing keys beyond thread_id; no presence; no canvas rail; no resume.

## Command / revision primitives
- Status: ❌
- Where: None. No `base_rev`/head revision or command envelopes in repo.

## Artifact storage patterns
- Status: ⚠️
- Where: `engines/media_v2/*` (assets/artifacts models/routes/service), `engines/media_v2/service.py` (default `S3MediaStorage` using `RAW_BUCKET` + `boto3`, local fallback), `engines/nexus/raw_storage/*` (S3 presign/register), `engines/storage/gcs_client.py` (GCS helper still present but not default).
- Behavior: Media uploads default to S3 with key `tenants/{tenant_id}/{env}/media_v2/{asset_id}/{filename}`; Firestore or in-memory repo for metadata; raw storage service presigns S3 uploads at `tenants/{tenant_id}/{env}/raw/...`. Routes still lack auth/RequestContext. Lineage via `parent_asset_id`, `meta`.
- Gaps: `engines/nexus/raw_storage/routes.py` still broken (missing kill_switch/limiter imports); media_v2 routes unauthenticated; tenant scoping must be enforced.

## Mandatory Q&A (Repo Facts)
1) WebSocket infra? Yes: `engines/chat/service/ws_transport.py` (`/ws/chat/{thread_id}`), no auth/tenant, in-memory only, no resume/heartbeat.  
2) SSE endpoints? Yes: `engines/chat/service/sse_transport.py` (`GET/POST /sse/chat/{thread_id}`), no auth/tenant, no reconnect/Last-Event-ID.  
3) Revision/commit log concept? None; no revision heads in Nexus/media/timeline.  
4) Canonical persistence layer today? Firestore-backed repositories when GCP libs present; otherwise in-memory. Binary storage defaults to S3 (`RAW_BUCKET` via `boto3`) for media_v2 and raw storage; GCS helper remains but is not the default path; local temp fallback in absence of config.  
5) Canonical way to write to Nexus? Through `engines/nexus/backends` (`get_backend`) invoked by chat pipeline and DatasetEvent logger. Search/index/cards/packs/settings use backend abstraction but some routes are incomplete.  
6) Event logging canonical? DatasetEvent + PII strip via `engines/logging/events/engine.py`; EventLogEntry helper; missing deeper audit trails or action-level trace IDs.  
7) Tenancy/auth guard helpers? `RequestContext` and `get_auth_context` exist; many routes (chat/media/video*) do not use them. Where used (budget, kill_switch, firearms, temperature, analytics_events, vector_explorer, memory, identity keys/auth), tenant enforcement is applied.
