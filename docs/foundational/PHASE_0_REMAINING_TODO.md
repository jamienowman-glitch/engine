# Phase 0 Remaining TODO (Authoritative)

Each item is atomic, lane-tagged, and tied to acceptance verification. Secrets/Selecta/GSM/Stripe/Cognito remain deferred (Lane4).

## Lane1 — Control-Plane Primitives ✅ CLOSED

**Status:** All T1.1 through T1.3 **COMPLETED** by Worker1 (2025-12-27)

- **T1.1 Implement Surface + App models, repos, routes** ✅ DONE  
  Completed:
  - Surface model: `s_{uuid}` prefixed ID, tenant-scoped (engines/identity/models.py:103-119)
  - App model: `a_{uuid}` prefixed ID, tenant-scoped (engines/identity/models.py:121-137)
  - CRUD routes: `/control-plane/surfaces`, `/control-plane/apps` with auth guards (engines/identity/routes_control_plane.py:16-110)
  - Repository: InMemory + Firestore implementations with tenant scoping (engines/identity/repository.py:149-176)

- **T1.2 Implement ControlPlaneProject (canonical registry)** ✅ DONE  
  Completed:
  - Project model: Keyed by (tenant_id, env, project_id), separate from video_timeline domain (engines/identity/models.py:139-159)
  - CRUD routes: `/control-plane/projects` with auth guards and env filtering (engines/identity/routes_control_plane.py:112-162)
  - Repository: InMemory + Firestore with composite key support (engines/identity/repository.py:179-229)
  - Firestore collections: `control_plane_projects` storing canonical project registry

- **T1.3 Signup provisioning (create default project)** ✅ DONE  
  Completed:
  - Modified signup to create `(tenant_id, env="dev", project_id="default")` project on new tenant creation (engines/identity/routes_auth.py:39-48)
  - Default project is now durable, queryable control-plane record (not ephemeral header value)

## Lane3 — Routing Registry & Real Infra ✅ CLOSED

**Status:** All T3.1 through T3.4 **COMPLETED** by Worker2 (2025-12-27)

- **T3.1 Implement routing registry + CRUD tests** ✅ DONE  
  Completed: Registry module exists with Firestore + InMemory implementations (engines/routing/registry.py). Startup validation enforces all required resource_kinds configured.  
  Verified: `routing_registry()` raises `MissingRoutingConfig` if unset; no env/memory/noop fallbacks reachable in production.

- **T3.2 Rewire mounted services to registry (remove env defaults)** ✅ DONE  
  Completed:
  - Feature flags: Enforces Firestore-only (engines/feature_flags/repository.py:54-89)
  - Video timeline: Removed InMemory fallback (engines/video_timeline/service.py:439-446)
  - Media V2: Enforces S3 + blocks LocalMediaStorage (engines/media_v2/service.py:56-76)
  - Raw storage: Enforces RAW_BUCKET at init (engines/nexus/raw_storage/repository.py:37-48)
  - Routing registry backend: Requires Firestore in production (engines/routing/registry.py:166-191)  
  
  No more silent env/memory/noop/localhost/local fallbacks in production paths.

- **T3.3 Startup validation for routed services** ✅ DONE  
  Completed: `startup_validation_check()` in engines/routing/manager.py:26-69 called at app startup (engines/chat/service/server.py:58-70).  
  Behavior: App fails at startup if any required resource_kind missing or configured with disallowed backend (memory/noop/local/tmp/localhost). Error names the resource_kind and scope.

- **T3.4 Block noop/local/tmp in prod path** ✅ DONE  
  Completed:
  - Nexus noop: Blocked with `RuntimeError` (engines/nexus/backends/__init__.py:1-32)
  - RAW_BUCKET: Validated at S3RawStorageRepository init (engines/nexus/raw_storage/repository.py:37-48)
  - LocalMediaStorage: Removed; media_v2 requires S3 (engines/media_v2/service.py:56-76)  
  
  Production wiring rejects noop/local/tmp unless explicit test flag (via `set_routing_registry()`).

- **T3.5 Backend switch proof test** ⏭️ SKIPPED (Not required for Phase 0 closeout)  
  Note: Backend switching via registry is operational (no code barrier), but test suite deferred to Phase 1.

## Lane2 (acceptance gap only)
- **T2.1 Add project-required acceptance test**  
  Evidence: RequestContext requires project_id (engines/common/identity.py:22-115), but pytest target missing (`python3 -m pytest engines/common/tests/test_request_context.py::test_project_required` returned “not found”).  
  Definition of Done: test asserts 400 when project_id absent, 400/403 on mismatch, and success when provided; added to acceptance list.  
  Verify: `python -m pytest engines/common/tests/test_request_context.py::test_project_required`.  
  **Status:** Deferred to Lane2 worker. Not part of Lane3 real-infra enforcement.

## Deferred Lane4 (secrets)
- Secrets/Selecta/GSM/Stripe/Cognito changes are explicitly out of Phase 0 scope; track separately when Lane4 opens.
