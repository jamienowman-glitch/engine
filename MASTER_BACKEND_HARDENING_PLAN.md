# MASTER_BACKEND_HARDENING_PLAN

## Goals
- Lock down streaming transports with RequestContext, AuthContext, routing isolation, and trace propagation so SSE/WS clients cannot cross tenant boundaries.
- Harden Nexus and storage APIs with auth/GateChain enforcement so every external mutation passes KillSwitch → Firearms → StrategyLock → Budget/KPI/Temperature before persisting to Nexus or S3.
- Elevate logging/audit, feature-flag, and privacy infrastructure to production grade (immutable audit trails, tenant-0 overrides, training opt-out persistence).
- Provide reproducible multi-tenant guardrails for 1M+ tenants with traceable operations.

## Invariants
1. Every tenant-scoped route must depend on `get_request_context` + `get_auth_context` unless explicitly marked public and approved.
2. External/world mutations must run through the ordered gate chain; internal drafts (canvas-only) still emit audit events.
3. Streaming events carry `request_id`/`trace_id` and routing keys validated against `engines/realtime/isolation.py` registry.
4. S3/raw storage keys always start with `tenants/{tenant_id}/{env}/...` and register resolvable metadata in Nexus/Firestore.
5. Audit logging never swallows errors silently; failures must surface while not failing happy paths.

## Dependency order
1. PHASE_01 ensures streaming foundations (auth + replay + trace IDs) without which all transports remain untrusted.
2. PHASE_02 layers auth onto Nexus routes so control-plane integrations reference enabled tenants.
3. PHASE_03 fixes raw storage path issues to prevent broken S3 presign/register flows.
4. PHASE_04 upgrades logging backends (audit + trace) so downstream gate/feature phases can rely on immutable events.
5. PHASE_05 introduces tenant-0/global feature flags needed before gating blocks new permissions.
6. PHASE_06 implements GateChain enforcement for external mutations; depends on previous auth/audit guarantees.
7. PHASE_07 adds persistent privacy/train pref APIs so logging can respect opt-outs at scale.
8. PHASE_08 thickens realtime registry durability/throttles so isolation stays robust under load.

## Risk register
| Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- |
| SSE/WS auth regression | High | High | Run new pytest suites before merging; add guardrails around request dependencies. |
| Nexus route lockout | Medium | High | Add feature-flagged rollouts and keep old routes gated until tests cover membership. |
| Raw storage presign failure | High | Medium | Validate S3 key generation + integrate `create_presigned_post`. |
| Audit logger silent failure | Medium | High | Switch off no-op and ensure new audit emitter always returns failure to caller when write fails. |
| GateChain ordering mistakes | Low | High | Document sequence and reuse gate helper function with strong unit tests. |

## Definition of done (FE unblocking)
- SSE/WS chat endpoints accept requests only with valid `RequestContext`+`AuthContext` and expose resume semantics (Last-Event-ID for SSE, last_id/token for WS). FE can rely on deterministic route responses and no longer bypass transport ACLs.
- Nexus routes previously unauthenticated now fail early with 401/403 on missing auth; FE tests confirm `t_unknown` is unacceptable in production mode.
- Raw storage presign/register respond with real S3 URLs and consistent audit events so FE file uploads succeed.
- Audit logs surface traceable DatasetEvents with tenant/trace/actor IDs and respect privacy opt-outs; FE can query the audit stream for debugging.

## Do this first (minimum unblock set)
1. Fix chat SSE/WS transports to require `RequestContext`+`AuthContext`, validate routing keys via `verify_thread_access`/`verify_canvas_access`, and emit trace_ids tied to the request.
2. Apply auth+RequestContext to the Nexus HTTP routes listed in the Coverage Map (raw_storage, atoms, packs, cards, index/search, settings, runs, memory) plus any other control-plane REST endpoints without auth.
3. Correct `engines/nexus/raw_storage` route/service mismatch (introduce `create_presigned_post` wrapper or rename to match) and ensure generated S3 keys follow `tenants/{tenant_id}/{env}/...`.
4. Replace `_audit_logger` no-op with the logging engine and thread `request_id`/`trace_id` through DatasetEvents so every external mutation emits an immutable, traceable event.

## Phases
- PHASE_01_STREAMING_AUTH_AND_ISOLATION.md
- PHASE_02_NEXUS_AUTH_CONTEXT_ENFORCEMENT.md
- PHASE_03_RAW_STORAGE_PRESIGN_REGISTER_FIX.md
- PHASE_04_AUDIT_LOGGING_TRACE_IDS_IMMUTABILITY.md
- PHASE_05_GLOBAL_FEATURE_FLAGS_TENANT0_LAYER.md
- PHASE_06_GATECHAIN_EXTERNAL_MUTATIONS.md
- PHASE_07_PRIVACY_TRAIN_PREFS_API_PERSISTENCE.md
- PHASE_08_REALTIME_REGISTRY_DURABILITY_THROTTLES.md

## Lane Split (parallel execution)
- **Lane A (streaming + infra gate/apply)**: PHASE_01_STREAMING_AUTH_AND_ISOLATION, PHASE_03_RAW_STORAGE_PRESIGN_REGISTER_FIX, PHASE_06_GATECHAIN_EXTERNAL_MUTATIONS, PHASE_08_REALTIME_REGISTRY_DURABILITY_THROTTLES.  
  - Allowed modules: `engines/chat/service/ws_transport.py`, `engines/chat/service/sse_transport.py`, `engines/realtime/isolation.py`, `engines/chat/service/tests/*`, `engines/common/identity.py` (only if required for trace_id), `engines/nexus/raw_storage/routes.py`, `engines/nexus/raw_storage/service.py`, `engines/nexus/raw_storage/repository.py`, `engines/logging/event_log.py`, `engines/logging/audit.py`, `engines/nexus/raw_storage/tests/*`, `engines/nexus/hardening/gate_chain.py`, `engines/nexus/cards/routes.py`, `engines/nexus/memory/routes.py`, `engines/nexus/settings/routes.py`, `engines/nexus/index/routes.py`, `engines/nexus/runs/routes.py`, `engines/maybes/service.py`, `engines/analytics_events/service.py`, `engines/kill_switch/service.py`, `engines/firearms/service.py`, `engines/strategy_lock/service.py`, `engines/budget/service.py`, `engines/kpi/service.py`, `engines/temperature/service.py`, `engines/nexus/hardening/tests/*`, `engines/realtime/tests/*`, `engines/nexus/hardening/rate_limit.py` (throttle durability only).
- **Lane B (auth/logging/flags/privacy)**: PHASE_02_NEXUS_AUTH_CONTEXT_ENFORCEMENT, PHASE_04_AUDIT_LOGGING_TRACE_IDS_IMMUTABILITY, PHASE_05_GLOBAL_FEATURE_FLAGS_TENANT0_LAYER, PHASE_07_PRIVACY_TRAIN_PREFS_API_PERSISTENCE.  
  - Allowed modules: `engines/nexus/raw_storage/routes.py`, `engines/nexus/atoms/routes.py`, `engines/nexus/packs/routes.py`, `engines/nexus/cards/routes.py`, `engines/nexus/index/routes.py`, `engines/nexus/settings/routes.py`, `engines/nexus/runs/routes.py`, `engines/nexus/memory/routes.py`, `engines/nexus/*/tests/*`, `engines/logging/audit.py`, `engines/logging/events/engine.py`, `engines/dataset/events/schemas.py`, `engines/logging/events/tests/*`, `engines/maybes/service.py`, `engines/feature_flags/models.py`, `engines/feature_flags/repository.py`, `engines/feature_flags/service.py`, `engines/feature_flags/routes.py`, `engines/feature_flags/tests/*`, `engines/privacy/train_prefs.py`, `engines/privacy/routes.py`, `engines/privacy/tests/*`, `engines/common/identity.py` (only if user_id validation needed).

## Shared modules (single-threaded / integration-required)
- `engines/common/identity.py`, `engines/identity/auth.py`, FastAPI app mounts (`engines/chat/service/server.py`), routing contracts (`engines/realtime/contracts.py`), logging/audit helpers (`engines/logging/audit.py`, `engines/logging/events/engine.py`), gate services (`engines/kill_switch/service.py`, `engines/strategy_lock/service.py`).
- Any phase touching these is **INTEGRATION-REQUIRED**: PHASE_01 (trace_id helpers), PHASE_02 (shared deps), PHASE_03 (audit hooks), PHASE_04 (audit/logging), PHASE_06 (gate services), PHASE_07 (train_prefs used by logging).

## Merge protocol
- Branch names: `lane-a/<phase>` for Lane A, `lane-b/<phase>` for Lane B.
- Rebase policy: always `git fetch origin && git rebase origin/main` before opening PR; rebase again before merge to resolve shared-module drift.
- Integration PR order: merge Lane B PHASE_04 (audit/logging) before Lane A PHASE_06 (GateChain) to ensure audit hooks exist; otherwise, merge phases independently in numeric order with shared-module conflicts resolved on the integration branch.
- Required tests at merge gates: 
  - Lane A: `pytest engines/chat/service/tests engines/nexus/raw_storage/tests engines/nexus/hardening/tests engines/realtime/tests`
  - Lane B: `pytest engines/nexus/*/tests engines/logging/events/tests engines/feature_flags/tests engines/privacy/tests`
  - Full-run sanity (before final integration): `pytest engines/kill_switch/tests engines/strategy_lock/tests engines/budget/tests engines/kpi/tests engines/temperature/tests`

## Integration-required notes
- When touching shared modules, coordinate between lanes: do not land overlapping changes without rebasing on the latest main + the other lane’s branch. Integration PR should rerun the full required test commands above and resolve any schema/drift issues explicitly.
