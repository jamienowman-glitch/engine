# Phase 0 Final Sweep Report (Foundational Spine)

## VTE & Commands Run
- `git rev-parse HEAD` → `4dffa2455c40605a2fe1b0c0a44386c67a6066f9`.
- `git status --porcelain` → untracked docs only (`PHASE_0_LANE3_*`, `phase_0_definition_of_done.md`).
- Tests executed:
  - `python3 -m pytest engines/identity/tests/test_bootstrap.py::test_bootstrap_tenants_system_only` ✅ (passes; seeds only `t_system`).
  - `python3 -m pytest engines/common/tests/test_request_context.py::test_project_required` ❌ (test not found; gate missing).

## Scoreboard vs Phase 0 Acceptance Gates
- Bootstrap t_system only: **PASS** (engines/identity/routes_auth.py:83-104; test at engines/identity/tests/test_bootstrap.py:23-72).
- RequestContext requires tenant/env/project + guard coverage: **FAIL (gate missing)** — RequestContext enforces project_id (engines/common/identity.py:22-115) but acceptance test absent (pytest target missing).
- Routing registry CRUD + fail-fast: **FAIL** — No registry module; services still use env fallbacks (e.g., feature flags env default memory at engines/feature_flags/repository.py:54-83; rate_limit env default memory at engines/nexus/hardening/rate_limit.py:78-85).
- Real infra enforcement (no memory/noop/local tmp): **FAIL** — Env-based in-memory defaults remain (budget at engines/budget/repository.py:175-182; maybes at engines/maybes/repository.py:88-97; memory at engines/memory/repository.py:104-111; realtime registry default memory at engines/realtime/isolation.py:99-106; Nexus backend allows noop at engines/nexus/backends/__init__.py:8-24; media_v2 LocalMediaStorage at engines/media_v2/service.py:84-102; RAW_BUCKET deferred at engines/nexus/raw_storage/repository.py:38-72).
- Backend switch proof (data change -> backend change): **FAIL** — No test present (`tests/test_routing_backend_switch.py` absent).
- Raw bucket fail-fast + registry-provided storage: **FAIL** — RAW_BUCKET still env-based and validated only at use (engines/nexus/raw_storage/repository.py:38-72); registry not used.
- Chat bus + realtime registry durability: **FAIL** — Chat bus still env-driven Redis/localhost (engines/chat/service/transport_layer.py:65-82); realtime registry defaults to InMemory (engines/realtime/isolation.py:99-106); no durability test executed.

## Gap-to-Fix Mapping
- **G1 (Lane3)**: Routing registry not implemented; services keep env/memory/noop defaults (e.g., feature_flags at engines/feature_flags/repository.py:54-83; strategy_lock at engines/strategy_lock/state.py:8-16; budget at engines/budget/repository.py:175-182; memory at engines/memory/repository.py:104-111; realtime registry at engines/realtime/isolation.py:99-106; chat bus at engines/chat/service/transport_layer.py:65-82; Nexus noop allowed at engines/nexus/backends/__init__.py:8-24; RAW_BUCKET env at engines/media_v2/service.py:55-80 and engines/nexus/raw_storage/repository.py:38-72).  
  - Fix: Build registry + rewire selectors to registry; remove env defaults; enforce durable backends.  
  - Verify: `python -m pytest engines/routing/tests/test_registry.py` + `python -m pytest tests/test_real_infra_enforcement.py` + backend-switch test.
- **G2 (Lane3)**: Startup validation absent; app can start without registry config.  
  - Evidence: create_app lacks registry checks (engines/chat/service/server.py:68-118).  
  - Fix: Add startup validator covering all mounted resource_kinds; fail-fast with clear error.  
  - Verify: `python -m pytest engines/chat/tests/test_startup_routing_validation.py`.
- **G3 (Lane3)**: Real infra path still allows local/tmp/noop.  
  - Evidence: LocalMediaStorage default (engines/media_v2/service.py:84-102); S3RawStorageRepository defers RAW_BUCKET check (engines/nexus/raw_storage/repository.py:38-72); Nexus noop backend reachable (engines/nexus/backends/__init__.py:8-24).  
  - Fix: Gate prod path to durable storage only; guard RAW_BUCKET at startup; block noop/local unless explicit test flag.  
  - Verify: `python -m pytest engines/nexus/raw_storage/tests/test_raw_storage.py::test_missing_bucket_raises` + real-infra gate test.
- **G4 (Lane2 acceptance gap)**: Project-required gate missing.  
  - Evidence: RequestContext enforces project_id (engines/common/identity.py:22-115) but pytest target absent (command returned “not found”).  
  - Fix: Add test ensuring 400 without X-Project-Id/project_id and mismatch => 400/403; include in acceptance gates.  
  - Verify: `python -m pytest engines/common/tests/test_request_context.py::test_project_required`.
- **G5 (Lane3)**: Backend-switch proof missing.  
  - Evidence: No `tests/test_routing_backend_switch.py`; registry not present.  
  - Fix: Add test demonstrating backend change via registry data without redeploy (e.g., feature_flags or rate_limit).  
  - Verify: `python -m pytest tests/test_routing_backend_switch.py`.

## Phase 0 Status
- **Overall: FAIL** — Lane3 implementation/validation/backed tests absent; acceptance gate for project-required test missing; real-infra defaults still env/memory/noop/local.
