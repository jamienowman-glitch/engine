# Phase 0 Oracle Static Audit (No Tests)

## Scoreboard (PASS/FAIL/UNKNOWN)
- A) Tenancy + t_system only: **PASS**
- B) User + membership enforcement: **PARTIAL**
- C) RequestContext (project required): **PASS**
- D) Tenant modes as data: **PASS**
- E) Surfaces/Apps/Projects primitives: **FAIL (surface/app missing)**
- F) Signup flow outcome: **PARTIAL**
- G) InMemory/noop/local/tmp inventory: **FAIL (defaults still reachable)**

## Evidence
- **A) Tenancy + t_system only**
  - Bootstrap seeds only `t_system` and seeds modes (engines/identity/routes_auth.py:83-118).
  - Tenant creation helper generates dynamic tenant IDs for signup (engines/identity/routes_auth.py:20-24).
  - Tenant ID regex enforced in RequestContext (engines/common/identity.py:11-35,26).
- **B) Membership enforcement**
  - Canonical guard functions: require_tenant_membership/require_tenant_role (engines/identity/auth.py:47-55).
  - Sample router usage: video render guards (engines/video_render/routes.py:26-83) call require_tenant_membership + assert_context_matches; analytics_events routes require membership (engines/analytics_events/routes.py:13-30); feature_flags routes require role (engines/feature_flags/routes.py:13-34).
  - Many routers use get_request_context + get_auth_context, but full coverage not exhaustively enforced here.
- **C) RequestContext contract**
  - RequestContext includes tenant_id/env/project_id and requires project_id (400 if missing) (engines/common/identity.py:22-115,103-105).
  - Resolution order: headers -> query -> body fallback; token validation enforces tenant membership (engines/common/identity.py:52-105,89-99).
  - assert_context_matches enforces tenant/env/project consistency (engines/common/identity.py:118-135).
- **D) Tenant modes**
  - Mode model (engines/identity/models.py:81-93).
  - Repository supports create/get (engines/identity/repository.py:35-153).
  - Seeding of enterprise/saas/lab in bootstrap_tenants (engines/identity/routes_auth.py:101-118) idempotent.
- **E) Surfaces / Apps / Projects**
  - Project is a first-class timeline object with CRUD routes (engines/video_timeline/routes.py:39-78) and models/service (engines/video_timeline/models.py, engines/video_timeline/service.py:436-458).
  - No control-plane Surface/App models or repos found (search shows only scene-engine geometry surfaces, not tenancy surfaces; apps only in routing schemas, not persisted).
- **F) Signup flow**
  - /auth/signup creates user, optional new tenant with dynamic id, and membership role owner (engines/identity/routes_auth.py:28-44).
  - Does not create project/surface/app during signup.
- **G) InMemory/noop/local/tmp inventory**
  - feature_flags env default memory (engines/feature_flags/repository.py:54-83).
  - strategy_lock env default InMemory (engines/strategy_lock/state.py:8-16).
  - kpi env default InMemory (engines/kpi/service.py:13-20).
  - budget env default InMemory (engines/budget/repository.py:175-182).
  - maybes env default InMemory (engines/maybes/repository.py:88-97).
  - memory env default InMemory (engines/memory/repository.py:104-111).
  - analytics_events env default InMemory (engines/analytics_events/service.py:22-29).
  - rate_limit env default memory (engines/nexus/hardening/rate_limit.py:78-85).
  - firearms env default InMemory (engines/firearms/repository.py:117-124).
  - page_content env default InMemory (engines/page_content/service.py:21-28).
  - seo env default InMemory (engines/seo/service.py:11-18).
  - realtime registry default InMemory (engines/realtime/isolation.py:99-106).
  - chat bus env-driven redis/localhost, disallows “memory” but still env-based (engines/chat/service/transport_layer.py:65-82).
  - nexus backend allows noop (engines/nexus/backends/__init__.py:8-24).
  - media_v2 LocalMediaStorage (local/tmp) fallback and RAW_BUCKET env requirement (engines/media_v2/service.py:55-102).
  - raw_storage RAW_BUCKET deferred check (engines/nexus/raw_storage/repository.py:38-72).
  - timeline repo falls back to InMemory on Firestore failure (engines/video_timeline/service.py:436-445).
  - Routing registry exists but defaults to InMemory when ROUTING_REGISTRY_BACKEND unset (engines/routing/registry.py:161-173).

## Gaps / Remaining TODOs (Atomic)
- **GAP-A1 (PASS verified, monitor):** Keep bootstrap seeding limited to `t_system`; no action now.
- **GAP-B1 (Lane2/Lane guards):** Audit all mounted routers for require_tenant_membership usage; add guards where missing. Done when every router in engines/chat/service/server.py:68-118 uses get_request_context + get_auth_context + require_tenant_membership + assert_context_matches. Files: respective routes modules. Verify via added guard tests.
- **GAP-C1 (Lane2 acceptance):** Add project-required test (engines/common/tests/test_request_context.py) to enforce existing behavior. Done when missing project_id/mismatch returns 400/403 and test is present.
- **GAP-D1:** None (modes seeded) — keep seeding idempotent; no change.
- **GAP-E1 (Surface/App primitives missing):** Implement control-plane Surface and App models + repository + CRUD routes (identity or control_plane module). Done when Surface/App records can be created/read per tenant/env and referenced by RequestContext/scope; minimal Firestore or durable stub allowed. Files: new control_plane models/repos/routes.
- **GAP-E2 (Project persistence breadth):** Project exists in video_timeline domain but not control-plane; need control-plane Project record tied to tenant/env/project_id for cross-service routing. Done when control-plane Project collection exists and created on first project creation or signup hook. Files: identity/control_plane repo + linkage to timeline service creation.
- **GAP-F1 (Signup completeness):** Signup does not create surface/app/project. Done when signup optionally provisions default project (and future surface/app) per tenant, or explicit TODO to create via follow-up route. Files: engines/identity/routes_auth.py plus new control-plane repo.
- **GAP-G1 (Lane3 wiring):** All listed env/memory/noop/local/tmp defaults must be replaced with registry-driven durable selection or fail-fast. Done when production path cannot select InMemory/noop/LocalMediaStorage/localhost-redis and missing routing causes startup error. Files: selectors noted above + routing/manager/registry wiring.
- **GAP-G2 (Routing registry backend selection):** Registry defaults to InMemory if ROUTING_REGISTRY_BACKEND unset. Done when production mode requires durable registry or explicit fail; InMemory only allowed in tests. Files: engines/routing/registry.py (init policy) and startup validation.
- **GAP-G3 (Nexus noop + RAW_BUCKET deferral):** Block noop backend and enforce bucket at startup via registry. Files: engines/nexus/backends/__init__.py; engines/nexus/raw_storage/repository.py; routing wiring.

## Phase 0 verdict: NOT READY
Top 5 blockers:
1) No control-plane Surface/App primitives; Project not control-plane-backed (GAP-E1/E2).
2) Mounted services still allow env/memory/noop/local/tmp defaults; no fail-fast wiring (GAP-G1/G3).
3) Routing registry defaults to InMemory and is not enforced at startup (GAP-G2).
4) Membership guard coverage not fully audited across all routers (GAP-B1).
5) Signup does not provision project/surface/app; control-plane linkage missing (GAP-F1).
