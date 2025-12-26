# Phase 0 Risk Register (Foundational Spine)

- **R1 Hardcoded second tenant** — `t_northstar` auto-created alongside `t_system` (engines/identity/routes_auth.py:82-105).  
  Signal: POST `/auth/bootstrap/tenants` returns `t_northstar`. Mitigation: remove creation (P0-A1).
- **R2 Missing membership guards on media_v2 reads/writes** — GET/POST handlers lack require_tenant_membership on all paths (engines/media_v2/routes.py:73-137).  
  Signal: unauthenticated list/get succeeds in tests. Mitigation: enforce guards + context match (P0-B1).
- **R3 Feature flags default to in-memory via env** — backend defaults to `memory` when env unset (engines/feature_flags/repository.py:54-83).  
  Signal: app boot with no FEATURE_FLAGS_BACKEND silently uses memory. Mitigation: route via registry and fail fast (P0-C2, P0-F1).
- **R4 Strategy locks fall back to in-memory** — STRATEGY_LOCK_BACKEND default returns InMemory (engines/strategy_lock/state.py:8-16).  
  Signal: lock data lost on restart. Mitigation: registry-driven backend, prod disallows memory (P0-C2, P0-F1).
- **R5 Realtime registry defaults to memory** — REALTIME_REGISTRY_BACKEND default `memory` (engines/realtime/isolation.py:99-109).  
  Signal: thread/canvas ownership lost after restart. Mitigation: require durable registry and fail missing config (P0-E1).
- **R6 Raw storage bucket optional at init** — S3 repo defers RAW_BUCKET validation until use (engines/nexus/raw_storage/repository.py:38-47).  
  Signal: first presign call 500 due to missing bucket. Mitigation: registry supplies bucket and startup validation (P0-C2).
- **R7 Nexus backend allows noop** — get_backend returns Noop when NEXUS_BACKEND=noop (engines/nexus/backends/__init__.py:8-23).  
  Signal: writes discarded silently. Mitigation: restrict to durable backends via registry (P0-C2, P0-F1).
- **R8 Secrets still read directly from env** — runtime_config exposes many env getters (engines/config/runtime_config.py:59-179) bypassing keys/selecta path.  
  Signal: grep os.getenv in infra modules. Mitigation: route secrets through keys/selecta (P0-D1).
- **R9 Secret dev fallbacks usable in prod if env mis-set** — selecta resolves MissingKeyConfig via env when env classified as dev/local (engines/common/selecta.py:66-99).  
  Signal: prod env mis-set to dev allows env secrets. Mitigation: enforce env classification + runtime checks (P0-D1).
- **R10 Raw storage metadata persistence is a no-op** — S3RawStorageRepository.persist_metadata pass-through (engines/nexus/raw_storage/repository.py:98-101).  
  Signal: metadata absent after upload. Mitigation: implement durable metadata path tied to registry backend (P0-C2).

## PATCH 2025-12-26 — DoD Clarifications C1–C3
- **R11 Multi-tenant drift via seeded `t_northstar`** — bootstrap still creates `t_northstar` (engines/identity/routes_auth.py:82-105) and tests expect it (engines/identity/tests/test_bootstrap.py:31-33).  
  Signal: POST `/auth/bootstrap/tenants` returns `t_northstar`. Mitigation: P0-A1 removes seed and updates test; gate in acceptance tests.
- **R12 Project context missing** — RequestContext lacks `project_id` (engines/common/identity.py:22-102) while many routes operate on projects without guard (e.g., engines/video_timeline/routes.py:17-53).  
  Signal: requests without project_id still succeed; cross-project confusion possible. Mitigation: P0-A3 adds project_id to RequestContext + guard; acceptance test `test_project_required`.
- **R13 Tenant modes absent as data** — No mode metadata persisted; `enterprise/saas/lab` not defined anywhere (confirmed by lack in identity code; only incidental substring hits via `rg -n \"enterprise|saas|lab\" engines/identity`).  
  Signal: future mode checks have no source of truth. Mitigation: P0-G1 seeds modes under `t_system` with CRUD/read and attaches to RequestContext (metadata only).
