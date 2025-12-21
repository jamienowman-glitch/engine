

A1) WebSocket

Status: ⚠️ exists but stub/partial
Where: engines/chat/service/ws_transport.py, mounted in engines/chat/service/server.py
How it behaves: FastAPI @router.websocket("/ws/chat/{thread_id}"); accepts any connection (no auth/tenant); in-memory ConnectionManager keyed by thread_id; broadcasts JSON {"type": "...", "data": ...} to all sockets on same thread; subscribes to in-memory bus and unsubscribes on disconnect; no persistence or backfill.
Public interface: /ws/chat/{thread_id} (WebSocket)
Notes for FE: No tenant/project scoping, no reconnect/backoff semantics, no presence/ping handling; state lost on process restart.
A2) SSE

Status: ⚠️ exists but stub/partial
Where: engines/chat/service/sse_transport.py, mounted in engines/chat/service/server.py
How it behaves: StreamingResponse generator sends event: message with JSON payload {"event":"message","data":{...}} per chat bus message; uses in-memory async queue per thread_id; no auth/tenant checks.
Public interface: GET /sse/chat/{thread_id}, POST /sse/chat/{thread_id} (sends message)
Notes for FE: Same thread-local, process-local scope as WS; no heartbeat/retry hints; consumers must implement SSE reconnect themselves.
A3) Chat transport layer

Status: ⚠️ exists but stub/partial
Where: engines/chat/service/http_transport.py, ws_transport.py, sse_transport.py, transport_layer.py, pipeline.py, mounted via engines/chat/service/server.py
How it behaves: In-memory bus (bus.add_message/subscribe) per thread_id; HTTP CRUD for threads/messages; posting calls process_message which logs a DatasetEvent, writes a Nexus snippet, calls Vertex via llm_client.stream_chat (tokens buffered, not streamed), then posts a single agent message; no auth/tenant bindings.
Public interface: /chat/threads GET/POST, /chat/threads/{id}/messages GET/POST, /ws/chat/{id}, /sse/chat/{id}
Notes for FE: Do not assume streaming tokens or durability; requires Vertex libs/env to respond; multi-tenant/context must be added externally.
A4) Event streaming infrastructure

Status: ⚠️ exists but stub/partial
Where: engines/chat/service/transport_layer.py (in-memory pub/sub); DatasetEvent logging via engines/logging/events/engine.py to Nexus backends
How it behaves: Only process-local pub/sub keyed by thread; DatasetEvents are written synchronously to Nexus backend (Firestore/BigQuery/memory/noop) with PII strip, no fan-out/gossip bus.
Public interface: None beyond chat transports and DatasetEvent logger
Notes for FE: No shared event bus or cross-service stream; no “gossip/meta” channel.
B5) RequestContext

Status: ✅ exists & used
Where: engines/common/identity.py
How it behaves: Pydantic model with tenant_id (pattern ^t_), env (dev|staging|prod|stage normalized), optional user_id, membership_role, auth_subject, is_system; built by get_request_context from headers (X-Tenant-Id, X-Env, X-User-Id, Authorization optional JWT decode) or query/body fallback; raises 400 if tenant/env missing.
Public interface: FastAPI dependency get_request_context
Notes for FE: Must send tenant/env headers; JWT optional but when provided must match tenant; no implicit defaults.
B6) Tenant + env isolation

Status: ⚠️ exists but stub/partial
Where: Enforced on routes using Depends(get_request_context) + require_tenant_membership/role (budget, analytics_events, kill_switch, strategy_lock, temperature, firearms, memory, vector_explorer, etc.)
How it behaves: Context validator checks tenant/env; some services also assert body tenant/env matches; many media/video/chat routes ignore RequestContext entirely.
Public interface: Route dependencies as above
Notes for FE: Do not assume all APIs scope tenant/env—video/render/timeline/media_v2/chat bypass auth/scoping today.
B7) Auth

Status: ⚠️ exists but stub/partial
Where: engines/identity/jwt_service.py, engines/identity/auth.py, engines/identity/routes_auth.py
How it behaves: HS256 JWT issuer/decoder using tenant key store or AUTH_JWT_SIGNING env; optional Cognito verifier; get_auth_context requires Bearer token else 401; bootstrap creates tenant/membership for Cognito users; only some routes depend on it.
Public interface: /auth/signup, /auth/login, /auth/refresh, /auth/me, /auth/bootstrap
Notes for FE: Large surface (chat/video/media) has no auth; where enforced, roles come from token role_map.
B8) Roles

Status: ⚠️ exists but stub/partial
Where: engines/identity/models.py (owner|admin|member|viewer), enforced via require_tenant_role in selected routes (keys, firearms, budget, kill_switch, temperature)
How it behaves: Role checks only run on routes that opt in; rest accept any authenticated member or no auth.
Public interface: Role-enforced routes noted above
Notes for FE: Do not assume consistent role gating; many endpoints are open once tenant header is present.
C9) Revisioning / optimistic concurrency

Status: ❌ not present
Where: n/a
How it behaves: No base_rev/monotonic revision fields; CRUD overwrites in place (timeline, video, media, cards).
Public interface: n/a
Notes for FE: No optimistic concurrency primitives exist.
C10) Command submission pattern

Status: ❌ not present
Where: n/a
How it behaves: No command envelope endpoints; mutations are direct resource posts/patches.
Public interface: n/a
Notes for FE: Any “command” model would be net-new.
C11) Conflict handling

Status: ❌ not present
Where: n/a
How it behaves: Only ad-hoc HTTPException messages per route; no shared error codes.
Public interface: n/a
Notes for FE: Expect inconsistent error shapes; no standardized conflict codes.
D12) Signals registry / personalization

Status: ❌ not present
Where: n/a
How it behaves: No registry or bindings for signals/personalization.
Public interface: n/a
Notes for FE: Treat as absent.
D13) Variant assignment / experiments

Status: ❌ not present
Where: n/a
How it behaves: No A/B assignment or exposure logging implemented.
Public interface: n/a
Notes for FE: No experiment hooks.
D14) Policy/privacy filter

Status: ⚠️ exists but stub/partial
Where: engines/guardrails/pii_text/engine.py, engines/privacy/train_prefs.py, engines/logging/events/engine.py
How it behaves: DatasetEvents run through PII detector and training opt-out before persisting; training prefs stored in-memory by default; no request-time PII stripping for other payloads.
Public interface: Indirect via DatasetEvent logging
Notes for FE: No general PII filter for uploads/chat payloads; only logging path applies policy.
E15) Accessibility audit

Status: ❌ not present
Where: n/a
How it behaves: No service or endpoints.
Public interface: n/a
Notes for FE: Nothing to integrate.
E16) Performance audit / budgets (page/CWV)

Status: ❌ not present
Where: n/a (only LLM/budget tracking exists separately)
How it behaves: No page-weight/CWV tooling.
Public interface: n/a
Notes for FE: No frontend performance auditor.
E17) Layout validator

Status: ❌ not present
Where: n/a
How it behaves: No layout/breakpoint validation service.
Public interface: n/a
Notes for FE: No backend validation for layout graphs.
E18) Journey analyzer

Status: ⚠️ exists but stub/partial (only basic SEO configs)
Where: engines/seo/routes.py, engines/seo/service.py
How it behaves: Stores/retrieves per-surface/page SEO configs via Firestore/InMemory repo; no journey/flow analysis.
Public interface: /seo/pages GET/PUT, /seo/pages/{surface}/{page_type} GET
Notes for FE: Only static SEO metadata, no analyzer.
E19) EAA compliance pack

Status: ❌ not present
Where: n/a
How it behaves: No compliance module.
Public interface: n/a
Notes for FE: Nothing shipped here.
F20) Asset storage

Status: ✅ exists & used
Where: engines/media_v2/*, engines/storage/gcs_client.py
How it behaves: Media assets/artifacts stored via Firestore collections per tenant when GCP libs available, else in-memory; uploads saved to GCS buckets from env (RAW_BUCKET/DATASETS_BUCKET) or temp files fallback; artifacts reference parent asset with type and window metadata.
Public interface: /media-v2/assets (multipart or JSON register), /media-v2/assets/{id}, /media-v2/assets/{id}/artifacts, /media-v2/artifacts/{id}
Notes for FE: No auth/RequestContext on these routes; storage is GCS-only with temp-file fallback (no S3).
F21) Asset optimization pipeline

Status: ❌ not present
Where: n/a (no image/video optimization endpoints outside render-specific flows)
How it behaves: None.
Public interface: n/a
Notes for FE: No generic optimization service.
F22) Font pack manager

Status: ⚠️ exists but stub/partial
Where: engines/design/fonts/registry.py, JSON font configs under engines/design/fonts/
How it behaves: Local lookups for font metadata/presets and CSS tokens; not serving fonts over HTTP; video_text service attempts to resolve local font files or fallbacks.
Public interface: No routes; library functions get_font, get_preset, to_css_tokens
Notes for FE: No font hosting/subsetting API; only local helpers.
F23) Provenance ledger

Status: ⚠️ exists but stub/partial
Where: media_v2.DerivedArtifact.parent_asset_id, video_timeline Clip links to asset/artifact, origin_snippets adds upstream_artifact_ids in meta, DatasetEvent logging carries metadata.
How it behaves: Lineage recorded ad hoc in models/meta; no centralized ledger or queries.
Public interface: Through media_v2 and origin_snippets routes
Notes for FE: Provenance fields exist but no guaranteed completeness or audit queries.
F24) Export artifacts

Status: ✅ exists & used
Where: engines/video_render/routes.py (RenderResult with artifact_id), media_v2 artifact creation, video_render/jobs.py
How it behaves: Render endpoints plan/execute ffmpeg and register artifacts in media_v2; job listing supports filters; dry-run returns plan preview.
Public interface: /video/render, /video/render/dry-run, /video/render/jobs family
Notes for FE: No auth; artifacts stored in Firestore/memory with URIs; no bundle/lineage endpoints beyond artifact lookup.
G25) Tool registry

Status: ❌ not present (docs only)
Where: Planning doc docs/constitution/TOOL_REGISTRY.md
How it behaves: No runtime registry or enforcement.
Public interface: n/a
Notes for FE: Do not assume registry or validation exists.
G26) Firearms metadata on tools/actions

Status: ⚠️ exists but stub/partial
Where: engines/firearms/* (licence model/service/routes), DANGEROUS_ACTIONS in service.py
How it behaves: Licence issue/revoke/list/check per tenant/env with role checks; require_licence_or_raise checks actions against simple map; not linked to specific tools or transports.
Public interface: /firearms/licences CRUD, /firearms/licences/check/{subject_type}/{subject_id}, demo POST
Notes for FE: No automatic tagging of tools; FE cannot rely on firearms metadata being attached to actions.
H27) Nexus routes

Status: ⚠️ exists but stub/partial
Where: Mounted via engines/chat/service/server.py; modules engines/nexus/{raw_storage,atoms,cards,index,packs,settings,runs,memory,vector_explorer,vector_explorer/ingest}
How it behaves: Many routes depend on RequestContext + kill_switch/rate_limit but several files are incomplete/broken (raw_storage/atoms/packs routes reference missing imports/vars); implemented ones: /nexus/search (card search), /vector-explorer/scene, /vector-explorer/ingest, /nexus/settings/*, /nexus/memory/* (session/blackboard), /nexus/runs read derives from event log but backend query may be unsupported.
Public interface: See above; some endpoints likely error due to stubs.
Notes for FE: Treat raw_storage/atoms/packs routes as unusable until fixed; expect Firestore dependencies; auth enforced on the working ones.
H28) Influence packs

Status: ⚠️ exists but stub/partial
Where: engines/nexus/packs/service.py (+ incomplete routes.py)
How it behaves: Service queries index and wraps results into InfluencePack with CardRefs; routes missing imports/types (CreatePackRequest) so current HTTP surface is broken.
Public interface: Intended POST /nexus/influence-pack (currently broken)
Notes for FE: Not callable without fixing route definitions.
H29) Logging (DatasetEvent)

Status: ✅ exists & used
Where: Schema engines/dataset/events/schemas.py; logger engines/logging/events/engine.py; helper engines/logging/event_log.py; Nexus backends in engines/nexus/backends/*
How it behaves: DatasetEvent requires tenantId/env/surface/agentId/input/output; logger strips PII, applies training prefs, writes to Nexus backend (FireStore/BigQuery/memory/noop), emits stdout JSON; chat pipeline and analytics events use it.
Public interface: Indirect via services that call logging.events.engine.run or default_event_logger
Notes for FE: Event shape fixed as above; failures are swallowed (best effort) in some helpers.
I30) Surprises (existing backend capabilities)

Kill switch service (/kill-switches) enforces provider/action blocks per tenant/env with Strategy Lock guard.
Strategy Lock (/strategy-locks) with Three-Wise review hooks; actions like temperature updates gated.
Three-Wise reviewer stub (/three-wise/questions) storing approvals/verdicts per tenant.
Temperature corridors (/temperature/*) storing floors/ceilings/weights with role + strategy lock checks.
Budget usage tracker (/budget/usage*) attaches AWS identity metadata when provider="aws"; membership required.
Analytics events service (/analytics/events/pageview|cta-click) logs DatasetEvents with UTM/SEO fields.
Memory/blackboard store (/memory/session/messages, /memory/blackboards/{key}) tenant-scoped with auth.
BYOK/key management (/tenants/{id}/keys) with role enforcement and Secret Manager/GSM-backed storage.
Firearms licences can block dangerous actions via require_licence_or_raise; coupled with audit logging.
Video timeline/timeline CRUD (/video/projects, /video/render etc.) are open (no auth) and purely in-memory/Firestore stubs.
Media_v2 asset/artifact model used by render/audio pipelines; artifact kinds include masks, proxies, voice_enhanced, etc.
Origin snippets service adds lineage linking audio artifacts back to video windows (/origin-snippets/from-audio).
Nexus embedding/vector explorer uses Vertex configs resolved via runtime_config/selecta; emits usage events on ingest.
AWS debug routes (/debug/aws-identity, /debug/aws-billing-probe) require owner/admin; always return ok flag even on failure.
Training preference service influences DatasetEvent.train_ok but is in-memory; no user-facing routes yet.
Fonts registry + video_text renderer attempt to load Roboto Flex locally with fallbacks; unknown fonts raise.
Render engine includes ducking/mask/proxy/slowmo logic with chunked jobs; dry-run returns detailed ffmpeg plan metadata.
DatasetEvent logging may silently no-op if backend missing (try/except); do not assume persistence.
GCS-only storage helper (engines/storage/gcs_client.py) expects RAW/DATASETS buckets; raises if missing unless fallback path is taken.