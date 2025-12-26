# Phase 0 Acceptance Tests (Gated, copy/paste runnable)

Ordered gates to prove the Phase 0 spine. Commands assume uvicorn/app wiring at engines/chat/service/server.py:54-119 and bootstrap route at engines/identity/routes_auth.py:82-107.

1) **Bootstrap control plane (t_system only)**
   - Command: `SYSTEM_BOOTSTRAP_KEY=test python -m pytest engines/identity/tests/test_bootstrap.py::test_bootstrap_tenants_system_only`
   - Verifies bootstrap endpoint creates only `t_system` (no `t_northstar`).

2) **RequestContext + membership semantics**
   - Command: `python -m pytest engines/common/tests/test_request_context.py`
   - Verifies tenant/env required and mismatch handling (guards from engines/common/identity.py:38-115).
   - Follow with per-router guard sweep: `python -m pytest tests/test_route_guards.py`
   - Verifies mounted routers (e.g., media_v2 routes at engines/media_v2/routes.py:32-137) reject missing membership/tenant mismatch.

3) **Routing registry CRUD + fail-fast**
   - Command: `python -m pytest engines/routing/tests/test_registry.py`
   - Establishes registry exists (none today) and raises when resource_kind missing.
   - Command: `python -m pytest tests/test_routing_backend_switch.py`
   - Verifies a resource_kind backend change via registry data (no redeploy) is honored by a mounted service.

4) **Secrets path only via keys/selecta**
   - Command: `python -m pytest engines/billing/tests/test_secret_resolution.py`
   - Asserts Stripe/auth/infra modules pull secrets through selecta/keys (engines/common/selecta.py:22-139; engines/common/keys.py:44-113) with no direct os.getenv shortcuts.

5) **Persistence survives restart**
   - Command: `python -m pytest tests/test_persistence_restart.py`
   - Test stores tenant-scoped data via mounted router, restarts app (re-import create_app), and confirms records remain (covers services previously defaulting to memory such as feature_flags at engines/feature_flags/repository.py:54-83).

6) **Realtime durability (bus + registry)**
   - Command: `python -m pytest engines/chat/tests/test_realtime_durability.py`
   - Uses Redis backend (chat bus selector engines/chat/service/transport_layer.py:65-83) and Firestore registry (engines/realtime/isolation.py:99-109) to assert thread/canvas ownership persists across restart and Last-Event-ID replay works.

7) **Full integration smoke (app wiring)**
   - Command: `uvicorn engines.chat.service.server:app --port 8000 & sleep 5 && curl -f -H \"X-System-Key:test\" -X POST http://localhost:8000/auth/bootstrap/tenants && pkill -f \"uvicorn engines.chat.service.server\"`
   - Confirms mounted app responds and bootstrap path remains reachable after routing/guard changes.

## PATCH 2025-12-26 — DoD Clarifications C1–C3
- **C1 (single hardcoded tenant)**: Gate 1 already targets `t_system` only; ensure test fixture asserts `\"created\" == [\"t_system\"]`. Command remains `SYSTEM_BOOTSTRAP_KEY=test python -m pytest engines/identity/tests/test_bootstrap.py::test_bootstrap_tenants_system_only` (evidence: engines/identity/routes_auth.py:82-107; engines/identity/tests/test_bootstrap.py:31-33).
- **C2 (project required)**: Add gate `python -m pytest engines/common/tests/test_request_context.py::test_project_required` to assert RequestContext enforces `project_id` header/body and rejects missing/mismatched (current RequestContext lacks project: engines/common/identity.py:22-102).
- **C3 (tenant modes as data)**: Add gate `python -m pytest engines/identity/tests/test_tenant_modes.py` to verify seeded `enterprise/saas/lab` modes under `t_system` and CRUD/read attach to RequestContext.
