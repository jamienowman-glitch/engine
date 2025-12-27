# Phase 0 TODOs by Lane (Foundational Only)

## Lane 1 — Identity & Control Plane Data
- Evidence: Bootstrap currently auto-creates `t_system` and `t_northstar` (engines/identity/routes_auth.py:82-105); RequestContext enforces tenant regex `^t_[a-z0-9_-]+$` (engines/common/identity.py:22-115) but no control-plane records for surface/app/project/mode.
- TODO IDs: P0-A1, P0-A2, P0-G1.
- Dependencies: none; provides primitives other lanes depend on.
- Definition of verified: `python -m pytest engines/identity/tests/test_bootstrap.py::test_bootstrap_tenants_system_only` and new CRUD tests for mode/surface/app/project data pass; bootstrap response lists only `t_system`.

## Lane 2 — RequestContext & Membership Enforcement
- Evidence: RequestContext guard exists (engines/common/identity.py:38-115) but routes like media_v2 GET/POST lack require_tenant_membership on all paths (engines/media_v2/routes.py:73-137).
- TODO IDs: P0-B1, P0-B2.
- Dependencies: Lane 1 for tenant primitives; can proceed in parallel with routing work.
- Definition of verified: route-guard test suite passes (e.g., `python -m pytest engines/common/tests/test_request_context.py` and new per-router guard tests); unauthorized/mismatched tenant/env return 401/403/400 consistently.

## Lane 3 — Routing Registry & Persistent Backends
- Evidence: Multiple services default to in-memory/noop via envs (feature_flags backend env default memory at engines/feature_flags/repository.py:54-83; strategy_lock in engines/strategy_lock/state.py:8-19; KPI env fallback in engines/kpi/service.py:13-24; realtime registry memory default in engines/realtime/isolation.py:99-109; chat bus env default in engines/chat/service/transport_layer.py:65-83).
- TODO IDs: P0-C1, P0-C2, P0-F1.
- Dependencies: none for registry creation; P0-C2 and P0-F1 depend on registry API from P0-C1.
- Definition of verified: routing registry CRUD/unit tests pass; app startup fails without registry entries for mounted services; backend switch test (registry data change without redeploy) passes via `python -m pytest tests/test_routing_backend_switch.py`.

## Lane 4 — Secrets Resolution Unification
- Evidence: Secret resolution centralized in selecta/keys with dev env fallbacks (engines/common/selecta.py:22-139; engines/common/keys.py:44-113), but services still read secret env vars directly (runtime_config getters at engines/config/runtime_config.py:59-179).
- TODO IDs: P0-D1.
- Dependencies: Lane 3 registry for routing metadata; otherwise independent.
- Definition of verified: all infra/auth/billing modules pull secrets via keys/selecta; tests asserting no direct os.getenv secret reads pass (`python -m pytest engines/billing/tests -q` after adding coverage).

## Lane 5 — Realtime Durability (Bus + Registry)
- Evidence: Chat bus selection allows env default but rejects memory at runtime (engines/chat/service/transport_layer.py:65-83); realtime registry defaults to in-memory when Firestore unavailable (engines/realtime/isolation.py:99-109).
- TODO IDs: P0-E1.
- Dependencies: Lane 3 registry for routing data; optional identity lane for tenant context.
- Definition of verified: Redis-only bus enforced and Firestore-backed registry required; durability tests using restart simulation pass (`python -m pytest engines/chat/tests/test_realtime_durability.py`).

## PATCH 2025-12-26 — DoD Clarifications C1–C3
- **Lane 1 additions (Identity/Control Plane)**: 
  - P0-A1 (C1) — remove `t_northstar` bootstrap + adjust tests (engines/identity/routes_auth.py:82-107; engines/identity/tests/test_bootstrap.py:31-33).
  - P0-G1 (C3 extension) — seed tenant modes (`enterprise|saas|lab`) as control-plane data owned by `t_system`; expose CRUD and attach to RequestContext (engines/common/identity.py:22-102 lacks mode today).
  - Definition of verified: mode CRUD and seeding tests pass (`python -m pytest engines/identity/tests/test_tenant_modes.py`); bootstrap test shows only `t_system`.
- **Lane 2 additions (Context & Guards)**:
  - P0-A3 (C2) — require `project_id` in RequestContext + routing guards. Evidence: RequestContext lacks project_id (engines/common/identity.py:22-102) while project APIs exist (engines/video_timeline/routes.py:17-53). Definition of verified: new RequestContext/project guard tests pass (`python -m pytest engines/common/tests/test_request_context.py::test_project_required`), and router guard suite updated.

## Lane 3 — Routing Registry & Real Infra (new docs)
- References: PHASE_0_LANE3_TODO.md, PHASE_0_LANE3_ACCEPTANCE.md, PHASE_0_LANE3_RESOURCE_KIND_MAP.md.
- Scope: build routing registry, wire mounted services from create_app (engines/chat/service/server.py:68-118) off env/memory/noop defaults (evidence: feature_flags env default memory at engines/feature_flags/repository.py:54-83; strategy_lock at engines/strategy_lock/state.py:8-16; kpi at engines/kpi/service.py:13-20; budget at engines/budget/repository.py:175-182; maybes at engines/maybes/repository.py:88-97; memory at engines/memory/repository.py:104-111; analytics_events at engines/analytics_events/service.py:22-29; rate_limit at engines/nexus/hardening/rate_limit.py:78-85; firearms at engines/firearms/repository.py:117-124; page_content at engines/page_content/service.py:21-28; seo at engines/seo/service.py:11-18; realtime registry at engines/realtime/isolation.py:99-106; chat bus at engines/chat/service/transport_layer.py:65-82; nexus noop at engines/nexus/backends/__init__.py:8-24; media_v2/raw_storage RAW_BUCKET env at engines/media_v2/service.py:55-80 and engines/nexus/raw_storage/repository.py:38-72; timeline repo fallback at engines/video_timeline/service.py:436-445).
- TODO IDs: P0-C1 (routing registry), P0-C2 (service wiring), P0-C3 (startup validation), P0-F1 (disallow memory/noop/local tmp in prod), P0-C4 (backend switch test).
- Definition of verified: see PHASE_0_LANE3_ACCEPTANCE.md commands.

## Closeout (Phase 0 Finalization)
- Remaining gaps summarized in PHASE_0_REMAINING_TODO.md and PHASE_0_CLOSEOUT_TODO.md; acceptance gates in PHASE_0_CLOSEOUT_ACCEPTANCE.md; resource_kind audit in PHASE_0_CLOSEOUT_RESOURCE_KIND_AUDIT.md.
- Focus: fail-fast on missing routing for all mounted routers, remove env/memory/noop/local-tmp defaults from production path, add backend-switch proof test, and add project-required acceptance test. Secrets remain deferred.
