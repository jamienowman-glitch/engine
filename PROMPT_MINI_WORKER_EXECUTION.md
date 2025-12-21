# PROMPT_MINI_WORKER_EXECUTION

## Mission
- Execute backend hardening phases in order (Phase 01 → 02 → 03 → 04 → 05 → 06 → 07).
- One PR per phase (no combining). Follow scope locks. No refactors/formatting-only changes.

## Global Scope Lock Rules
- Only touch files listed for the active phase.
- If you need to change anything outside the allowed list: STOP and report.
- Preserve existing behaviors outside the targeted fixes; no new endpoints/schemas.
- Always use `RequestContext` + `AuthContext` where mandated; never introduce `t_unknown`.

## Required Output Template (use in every status update)
- Current phase + substep:
- Files changed (paths):
- Tests run + results:
- What changed (1–3 bullets):
- Any blockers:
- Next action:

---

## Phase 01: Chat Rails Prod (WS/SSE hardening)
Start here checklist:
- Remove duplicate unauth SSE router; ensure only authenticated router is exported.
- Add RequestContext + AuthContext enforcement to WS/SSE; validate tenant/env via `verify_thread_access`.
- Add trace_id/request_id into StreamEvent meta; reject `t_unknown`.
- Update isolation env check if needed.

Allowed files:
- `engines/chat/service/ws_transport.py`
- `engines/chat/service/sse_transport.py`
- `engines/realtime/isolation.py`
- `engines/chat/service/tests/*`
- `engines/common/identity.py` (only if trace helper needed)

Tests to add:
- Negative: WS/SSE reject missing auth/context; cross-tenant blocked; trace_id present in events.

Tests to run:
- `pytest engines/chat/service/tests/test_ws_transport.py engines/chat/service/tests/test_sse_transport.py`

Stop conditions:
- Need to touch files outside allowed list.
- Mounting breaks other routers.

---

## Phase 02: Nexus Control Plane Prod (Auth/membership on Nexus routes)
Start here checklist:
- Add AuthContext + require_tenant_membership to raw_storage, atoms, packs, cards, index, settings, runs, memory routes.
- Add assert_context_matches for payload tenant/env where present.
- Preserve existing kill_switch/rate_limit checks.

Allowed files:
- `engines/nexus/raw_storage/routes.py`
- `engines/nexus/atoms/routes.py`
- `engines/nexus/packs/routes.py`
- `engines/nexus/cards/routes.py`
- `engines/nexus/index/routes.py`
- `engines/nexus/settings/routes.py`
- `engines/nexus/runs/routes.py`
- `engines/nexus/memory/routes.py`
- `engines/nexus/*/tests/*`

Tests to add:
- Negative: missing auth → 401; cross-tenant mismatch → 403/400 on representative routes.

Tests to run:
- `pytest engines/nexus/raw_storage/tests engines/nexus/atoms/tests engines/nexus/packs/tests engines/nexus/cards/tests engines/nexus/index/tests engines/nexus/settings/tests engines/nexus/runs/tests engines/nexus/memory/tests`

Stop conditions:
- Need to touch services/backends outside scope.

---

## Phase 03: Raw Storage Presign/Register Prod
Start here checklist:
- Align route call with actual presign method (fix missing `create_presigned_post` mismatch).
- Enforce AuthContext + assert_context_matches on presign/register.
- Ensure S3 key/URI prefix `tenants/{tenant}/{env}/raw/...`; log events with request_id/trace_id.

Allowed files:
- `engines/nexus/raw_storage/routes.py`
- `engines/nexus/raw_storage/service.py`
- `engines/nexus/raw_storage/repository.py`
- `engines/logging/event_log.py`
- `engines/logging/audit.py`
- `engines/nexus/raw_storage/tests/*`

Tests to add:
- Negative: missing auth; cross-tenant mismatch.
- Assert key prefix and event metadata contains request_id/trace_id.

Tests to run:
- `pytest engines/nexus/raw_storage/tests`

Stop conditions:
- Need to change storage backends beyond these files.

---

## Phase 04: Audit Logging + Trace Prod
Start here checklist:
- Wire `_audit_logger` to logging engine (no-op removed).
- Add trace_id/request_id/actor_type into DatasetEvents (metadata/fields).
- Ensure logging engine surfaces failures (no silent swallow).

Allowed files:
- `engines/logging/audit.py`
- `engines/logging/events/engine.py`
- `engines/dataset/events/schemas.py`
- `engines/logging/events/tests/*`
- `engines/maybes/service.py` (metadata pass-through only)

Tests to add:
- Negative: backend error surfaces (no silent swallow).
- Trace/actor metadata present in emitted event.

Tests to run:
- `pytest engines/logging/events/tests`

Stop conditions:
- Schema changes require touching other modules.

---

## Phase 05: GateChain External Mutations Prod
Start here checklist:
- Implement GateChain (KillSwitch → Firearms → StrategyLock/ThreeWise → Budget/KPI/Temperature → Audit).
- Apply to external mutation endpoints: raw_storage register, cards, settings, runs, memory, maybes mutations, analytics_events writes.

Allowed files:
- `engines/nexus/hardening/gate_chain.py`
- `engines/maybes/service.py`
- `engines/analytics_events/service.py`
- `engines/nexus/raw_storage/routes.py`
- `engines/nexus/cards/routes.py`
- `engines/nexus/settings/routes.py`
- `engines/nexus/runs/routes.py`
- `engines/nexus/memory/routes.py`
- `engines/nexus/hardening/tests/*`

Tests to add:
- Negative: GateChain blocks missing auth/cross-tenant; blocks on KillSwitch/Firearms/StrategyLock/Temperature.
- Audit emit includes trace_id/request_id when allowed.

Tests to run:
- `pytest engines/nexus/hardening/tests`

Stop conditions:
- Need to modify services beyond allowed scope; missing data causes ambiguous gating (flag it).

---

## Phase 06: Storage Prefix Enforcement Prod
Start here checklist:
- Enforce tenant/env prefixes in media_v2 and canvas artifacts.
- Reject prod writes that fall back to local temp; ensure RequestContext used.

Allowed files:
- `engines/media_v2/service.py`
- `engines/media_v2/models.py`
- `engines/canvas_artifacts/service.py`
- `engines/canvas_artifacts/router.py`
- `engines/media_v2/tests/*`
- `engines/canvas_artifacts/tests/*`

Tests to add:
- Negative: missing tenant/env/auth rejected; cross-tenant rejected.
- Key prefix assertions.

Tests to run:
- `pytest engines/media_v2/tests/test_media_v2_endpoints.py engines/canvas_artifacts/tests/test_artifacts.py`

Stop conditions:
- Need to change other storage backends or media routes outside scope.

---

## Phase 07: Small Leaks Cleanup Prod
Start here checklist:
- Add AuthContext to temperature `/config`.
- Add RequestContext/Auth to chat HTTP transport; remove `t_unknown` usage in chat pipeline events.

Allowed files:
- `engines/temperature/routes.py`
- `engines/chat/service/http_transport.py`
- `engines/chat/pipeline.py`
- `engines/temperature/tests/*`
- `engines/chat/tests/*` (auth/context + pipeline tenant tests)

Tests to add:
- Negative: temperature config unauth/cross-tenant blocked.
- Chat HTTP missing auth/context blocked; events carry real tenant/env/request_id (no `t_unknown`).

Tests to run:
- `pytest engines/temperature/tests/test_temperature_routes.py engines/chat/tests`

Stop conditions:
- Need to modify WS/SSE or Nexus beyond scope; FE contract changes unclear.
