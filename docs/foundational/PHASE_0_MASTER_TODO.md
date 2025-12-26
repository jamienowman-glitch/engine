# Phase 0 — Foundational TODO (System Spine)

## Executive Summary
- Phase 0 locks the control plane: tenant/user/surface/app/project primitives must be first-class, with only `t_system` hardcoded (engines/identity/routes_auth.py:82-107).
- RequestContext must be uniform and enforced on every mounted route (engines/common/identity.py:22-115).
- Real infra becomes the default: all mounted services must select durable backends from a routing registry (none exists today) instead of env-var fallbacks; in-memory/noop/local-temp are test-only.
- Secrets resolve through the single resolver path (runtime_config + selecta + keys); scattered os.getenv usage for infra/auth/billing must be removed.
- Realtime substrate (chat bus, registry) must be durable-by-default (Redis + Firestore) with fail-fast when missing.

## Truth from repo today (evidence)
- Tenants bootstrap hardcodes `t_system` and `t_northstar` via `/auth/bootstrap/tenants` and SYSTEM_BOOTSTRAP_KEY (engines/identity/routes_auth.py:82-107).
- RequestContext normalization + context guards (engines/common/identity.py:22-115); assert_context_matches used across routers.
- Main app mounts many routers including feature_flags, strategy_lock, budget, kpi, maybes, memory, analytics_events, raw_storage, media_v2, etc. (engines/chat/service/server.py:68-118).
- Backend selection via env defaults to in-memory for many services: feature_flags (engines/feature_flags/repository.py:58), strategy_lock (engines/strategy_lock/state.py:9-16), kpi (engines/kpi/service.py:14-20), budget (engines/budget/repository.py:176-182), maybes (engines/maybes/repository.py:89-97), memory (engines/memory/repository.py:105-111), analytics_events (engines/analytics_events/service.py:23-29), rate_limit (engines/nexus/hardening/rate_limit.py:79-85), firearms (engines/firearms/repository.py:118-124), page_content (engines/page_content/service.py:22-28), seo (engines/seo/service.py:12-18), realtime registry (engines/realtime/isolation.py:99-106). Nexus backend allows noop (engines/nexus/backends/__init__.py:8-24). Media_v2/raw_storage require RAW_BUCKET (engines/media_v2/service.py:55-69; engines/nexus/raw_storage/repository.py:39-46).
- Secrets/config entrypoints: runtime_config getters for buckets/vector/models/secrets (engines/config/runtime_config.py:60-140); selecta slot mapping (engines/common/selecta.py:22-99,131-137); env-first key resolver (engines/common/keys.py:59-105).
- Realtime bus defaults to memory (but code forbids it) and needs Redis; defaults use envs (engines/chat/service/transport_layer.py:67-72). Registry defaults to in-memory (engines/realtime/isolation.py:99-106).

## Target State (Phase 0 DoD mapping)
- 0.1 Primitives & naming: Only `t_system` hardcoded; other tenants must be data-backed. Introduce control-plane data for surface/app/project modes (enterprise/saas/lab) without code changes to product behavior.
- 0.2 RequestContext: All mounted routers require RequestContext + require_tenant_membership + assert_context_matches; uniform 401/403/400 semantics.
- 0.3 Routing registry: Central data-driven registry keyed by resource_kind -> backend config; services query registry, not env vars. Missing config fails fast.
- 0.4 Secrets: Single resolver path (runtime_config/selecta/keys); remove direct os.getenv for secrets/backends except minimal bootstrap.
- 0.5 Persistence: Mounted routers never use InMemory/Noop/Local-temp defaults; production path must hard-fail missing config; tests may inject InMemory via setters.
- 0.6 Realtime substrate: CHAT_BUS_BACKEND must be Redis (or configured alternative) and registry durable (Firestore) by default; startup fails otherwise; thread/canvas ownership survives restart.
- 0.7 Tenant modes (Enterprise/SaaS/Lab) stored as control-plane data; runtime can read/attach; no behavior changes yet.
- 0.8 No env-var-driven defaults for backends; control-plane data drives routing.
- 0.9 Out of scope: logs/audit/trace/safety/memory product/realtime product/entitlements/artifacts.

## TODOs (Phase 0, stable IDs)

- **P0-A1: Remove hardcoded t_northstar from bootstrap**
  - Why: DoD allows only `t_system` hardcoded; northstar must be data-driven.
  - Change: engines/identity/routes_auth.py:82-107 – drop t_northstar auto-create; allow bootstrap to create only t_system.
  - Acceptance: /auth/bootstrap/tenants creates only t_system; tests updated accordingly.
  - Verify: `python -m pytest engines/identity/tests/test_bootstrap.py::test_bootstrap_tenants_success`.
  - Safety: Do not change JWT issuance; only bootstrap behavior.

- **P0-A2: Add control-plane schema for tenant modes/surface/app/project**
  - Why: Need first-class records for modes (Enterprise/SaaS/Lab) and surface/app/project metadata.
  - Change: Add models + repository entries under engines/identity or new control_plane module; no behavior change.
  - Acceptance: CRUD schema and Firestore storage stubs exist with tenant/env keys; unit tests cover create/get.
  - Verify: `python -m pytest engines/identity/tests -k mode` (new tests).
  - Safety: No runtime wiring yet; data model only.

- **P0-B1: Enforce RequestContext + membership on all mounted routes**
  - Why: Some routes (e.g., media_v2 GET/list) lack require_tenant_membership; DoD demands uniform guard.
  - Change: audit routers from engines/chat/service/server.py list; ensure each FastAPI route includes get_request_context + get_auth_context + require_tenant_membership and assert_context_matches payload tenant/env.
  - Acceptance: Every mounted router uses both guards; unauthorized/mismatched -> 401/403/400 per identity rules.
  - Verify: `python -m pytest engines/media_v2/tests/test_media_v2_endpoints.py::test_get_requires_auth` and add similar guard tests per router.
  - Safety: Do not alter business logic; guards only.

- **P0-B2: Standardize RequestContext normalization**
  - Why: Query/body fallbacks exist; ensure env normalization + token/headers precedence documented and tested.
  - Change: Add tests in engines/common/tests for get_request_context covering headers/body/token precedence and 400/401/403 cases.
  - Acceptance: Tests assert expected codes and normalized env handling.
  - Verify: `python -m pytest engines/common/tests/test_request_context.py`.
  - Safety: No API shape change.

- **P0-C1: Introduce routing registry (resource_kind -> backend config)**
  - Why: Current env-var defaults cause drift; need centralized routing data.
  - Change: New module (e.g., engines/routing/registry.py) with Firestore-backed store keyed by resource_kind and tenant/env with required fields (backend, config, required secrets ref); runtime read-only for now. Add interface and Firestore impl.
  - Acceptance: Registry can set/get configs; missing configs raise; unit tests cover CRUD and missing case.
  - Verify: `python -m pytest engines/routing/tests/test_registry.py`.
  - Safety: Do not wire services yet; registry API only.

- **P0-C2: Wire services to routing registry (remove env defaults)**
  - Why: InMemory/noop/local fallbacks via env vars violate DoD.
  - Change: For each service below, replace env-based selection with registry lookup; if missing -> fail fast:
    - feature_flags (engines/feature_flags/repository.py:58),
    - strategy_lock (engines/strategy_lock/state.py:9-16),
    - kpi (engines/kpi/service.py:14-20),
    - budget (engines/budget/repository.py:176-182),
    - maybes (engines/maybes/repository.py:89-97),
    - memory (engines/memory/repository.py:105-111),
    - analytics_events (engines/analytics_events/service.py:23-29),
    - rate_limit (engines/nexus/hardening/rate_limit.py:79-85),
    - firearms (engines/firearms/repository.py:118-124),
    - page_content (engines/page_content/service.py:22-28),
    - seo (engines/seo/service.py:12-18),
    - realtime registry (engines/realtime/isolation.py:99-106),
    - nexus backend selection (engines/nexus/backends/__init__.py:8-24),
    - chat bus (engines/chat/service/transport_layer.py:67-72),
    - media_v2/raw_storage should read buckets from registry, not env (engines/media_v2/service.py:55-69; engines/nexus/raw_storage/repository.py:39-46).
  - Acceptance: App startup fails when registry lacks config; InMemory/Noop unreachable unless injected in tests.
  - Verify: `python -m pytest tests/test_real_infra_enforcement.py` plus service-specific guard tests; add a registry-driven backend switch test.
  - Safety: Keep test hooks (set_* service setters) intact; prod path must reject missing routing.

- **P0-D1: Centralize secrets through keys/selecta**
  - Why: Scattered os.getenv for secrets/billing/auth cause drift.
  - Change: Replace direct secret env reads (e.g., Stripe keys, Cognito issuer/audience) with keys/selecta lookup; keep minimal bootstrap via env for local only.
  - Acceptance: Stripe/Cognito and similar paths call key resolver; env-only path gated to dev flag.
  - Verify: `python -m pytest engines/billing/tests -q` (add) and identity/cognito tests for resolver usage.
  - Safety: Do not change token validation logic.

- **P0-E1: Realtime durability baseline**
  - Why: DoD requires Redis + durable registry by default.
  - Change: chat/service/transport_layer.py: enforce CHAT_BUS_BACKEND redis-only with startup failure otherwise; realtime/isolation.py: default Firestore registry, fail if unavailable.
  - Acceptance: App startup fails without Redis/Firestore config; tests cover rejection when misconfigured.
  - Verify: `python -m pytest engines/chat/tests/test_redis_transport.py -q` and new registry durability tests.
  - Safety: Keep test injection hooks for unit tests.

- **P0-F1: Persistence baseline (no InMemory in mounted app)**
  - Why: Mounted routers currently expose in-memory defaults.
  - Change: After routing registry wiring, remove fallbacks so production create_app path always uses durable backends; InMemory only via explicit test injection.
  - Acceptance: Running app without registry config raises; integration tests confirm durable backend paths.
  - Verify: `python -m pytest tests/test_real_infra_enforcement.py`.
  - Safety: Do not delete test doubles; guard with env/test flags.

- **P0-G1: Tenant mode control-plane data**
  - Why: DoD requires modes as data; no behavior yet.
  - Change: Add mode field to tenant record or dedicated collection under t_system; expose CRUD via control-plane routes.
  - Acceptance: Mode persisted and retrievable; defaults to “saas” when unspecified; tests cover roundtrip.
  - Verify: `python -m pytest engines/identity/tests -k mode`.
  - Safety: No runtime branching yet.

## Notes
- Out of scope: logging/audit/trace/safety/memory product/realtime product/entitlements/artifacts.
- Bootstrap config allowed: SYSTEM_BOOTSTRAP_KEY and minimal ADC creds; all other routing must be data-driven.

## PATCH 2025-12-26 — DoD Clarifications C1–C3
- **New/updated TODO IDs**
  - **P0-A1 (C1 reinforcement): Remove seeded `t_northstar` and tests expecting it.** Evidence: bootstrap hardcodes `t_northstar` (engines/identity/routes_auth.py:82-107) and test asserts it (engines/identity/tests/test_bootstrap.py:31-33). Acceptance: `/auth/bootstrap/tenants` returns only `t_system`; test `python -m pytest engines/identity/tests/test_bootstrap.py::test_bootstrap_tenants_system_only` added and passing. Safety: keep SYSTEM_BOOTSTRAP_KEY check intact.
  - **P0-A3 (C2): Project required in RequestContext + headers).** Evidence: RequestContext lacks project_id field (engines/common/identity.py:22-102); routers rely on project routing but do not enforce request context (e.g., video timeline project CRUD at engines/video_timeline/routes.py:17-53). Change: add `project_id` to RequestContext with header `X-Project-Id` (or controlled default lookup), require it on all mounted routers, and assert context matches. Acceptance: missing/unknown project -> 400; context mismatch -> 400/403; new tests `python -m pytest engines/common/tests/test_request_context.py::test_project_required` and router guard tests covering project_id. Safety: no business logic changes beyond guard/enforcement; allow explicit test injection for legacy paths.
  - **P0-G1 (C3 extension): Tenant modes as data (seeded).** Evidence: no tenant mode records exist; RequestContext has no mode field (engines/common/identity.py:22-102). Change: extend control-plane schema to store modes (`enterprise|saas|lab`) under `t_system`, seed those three modes, expose CRUD/read, and allow attaching mode to tenant + RequestContext (read-only). Acceptance: seed job populates modes; CRUD roundtrip tests pass (`python -m pytest engines/identity/tests/test_tenant_modes.py`); RequestContext includes optional mode derived from tenant lookup. Safety: no behavior branching in Phase 0; mode is metadata only.
- **Acceptance criteria/verification (added)**
  - `python -m pytest engines/identity/tests/test_bootstrap.py::test_bootstrap_tenants_system_only`
  - `python -m pytest engines/common/tests/test_request_context.py::test_project_required`
  - `python -m pytest engines/identity/tests/test_tenant_modes.py`
- **Notes**
  - C1 ensures first real tenant comes from normal signup (no hardcoded `t_northstar`).
  - C2 requires deciding source for `project_id` (header vs persisted default) and documenting it in RequestContext docs/tests.
  - C3 seeds `enterprise/saas/lab` as data owned by `t_system`, no runtime branching until later phases.
