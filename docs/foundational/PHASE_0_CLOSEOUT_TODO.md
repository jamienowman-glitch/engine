# Phase 0 Closeout TODO (Fail-Fast, No InMemory/Noop/LocalTmp Defaults)

Rules: Do not choose final vendors; enforce durable-only policy, fail fast on missing routing/config, and block memory/noop/local/tmp/default localhost Redis in production wiring. No secrets/GSM/Selecta changes.

## Worker A — Acceptance + Gates
- **P0-CLOSE-A1: Add registry CRUD + fail-fast tests**  
  Evidence: No registry module; services still env/memory (e.g., feature_flags env default memory at engines/feature_flags/repository.py:54-83; rate_limit env default memory at engines/nexus/hardening/rate_limit.py:78-85).  
  Files: engines/routing/tests/test_registry.py (new).  
  Invariants: Missing resource_kind raises; tenant/env/project scoping honored.  
  Verify: `python -m pytest engines/routing/tests/test_registry.py`.
- **P0-CLOSE-A2: Real-infra enforcement test suite**  
  Evidence: Env fallbacks to memory/noop/local (budget at engines/budget/repository.py:175-182; maybes at engines/maybes/repository.py:88-97; memory at engines/memory/repository.py:104-111; realtime registry default memory at engines/realtime/isolation.py:99-106; Nexus noop at engines/nexus/backends/__init__.py:8-24; media_v2 LocalMediaStorage at engines/media_v2/service.py:84-102; RAW_BUCKET deferred at engines/nexus/raw_storage/repository.py:38-72; chat bus localhost default at engines/chat/service/transport_layer.py:65-82).  
  Files: tests/test_real_infra_enforcement.py (new).  
  Invariants: Production create_app path refuses memory/noop/local/tmp/localhost Redis and missing routing entries.  
  Verify: `python -m pytest tests/test_real_infra_enforcement.py`.
- **P0-CLOSE-A3: Backend switch proof test**  
  Evidence: No backend-switch test exists.  
  Files: tests/test_routing_backend_switch.py (new).  
  Invariants: Changing registry data switches backend for a mounted resource_kind without redeploy.  
  Verify: `python -m pytest tests/test_routing_backend_switch.py`.
- **P0-CLOSE-A4: Project-required acceptance gate**  
  Evidence: RequestContext requires project_id (engines/common/identity.py:22-115) but test missing (python3 -m pytest ...::test_project_required not found).  
  Files: engines/common/tests/test_request_context.py.  
  Invariants: 400 when project_id absent; 400/403 on mismatch; success when provided.  
  Verify: `python -m pytest engines/common/tests/test_request_context.py::test_project_required`.
- **P0-CLOSE-A5: Startup validation gate**  
  Evidence: create_app lacks registry checks (engines/chat/service/server.py:68-118).  
  Files: engines/chat/tests/test_startup_routing_validation.py (new).  
  Invariants: startup fails with explicit resource_kind name when routing missing or set to disallowed backend.  
  Verify: `python -m pytest engines/chat/tests/test_startup_routing_validation.py`.

## Worker B — Fail-Fast Enforcement Wiring
- **P0-CLOSE-B1: Minimal routing registry contract**  
  Evidence: None exists; services rely on env defaults above.  
  Files: engines/routing/registry.py (new), engines/config/runtime_config.py (hook only).  
  Invariants: CRUD for resource_kind scoped by tenant/env/project; raises MissingRoutingConfig; no vendor specifics; allows durable-stub placeholder (non-memory/noop/local).  
  Verify: covered by P0-CLOSE-A1.
- **P0-CLOSE-B2: Rewire backend selectors to registry**  
  Evidence: Env/memory defaults in feature_flags (engines/feature_flags/repository.py:54-83), strategy_lock (engines/strategy_lock/state.py:8-16), kpi (engines/kpi/service.py:13-20), budget (engines/budget/repository.py:175-182), maybes (engines/maybes/repository.py:88-97), memory (engines/memory/repository.py:104-111), analytics_events (engines/analytics_events/service.py:22-29), rate_limit (engines/nexus/hardening/rate_limit.py:78-85), firearms (engines/firearms/repository.py:117-124), page_content (engines/page_content/service.py:21-28), seo (engines/seo/service.py:11-18), realtime registry (engines/realtime/isolation.py:99-106), chat bus (engines/chat/service/transport_layer.py:65-82), nexus backend (engines/nexus/backends/__init__.py:8-24), media_v2/raw_storage (engines/media_v2/service.py:55-102; engines/nexus/raw_storage/repository.py:38-72), timeline default (engines/video_timeline/service.py:436-445).  
  Files: those selectors + helper to fetch registry config.  
  Invariants: Production path cannot choose memory/noop/local/tmp/localhost Redis; missing registry entry raises clear error naming resource_kind and scope.  
  Verify: P0-CLOSE-A2, P0-CLOSE-A5.
- **P0-CLOSE-B3: Startup fail-fast hook**  
  Evidence: create_app lacks checks (engines/chat/service/server.py:68-118).  
  Files: engines/chat/service/server.py (add startup validation call), engines/routing/registry.py (validation helper).  
  Invariants: Application startup aborts if any mounted resource_kind missing or disallowed backend; message names resource_kind and scope.  
  Verify: P0-CLOSE-A5.
- **P0-CLOSE-B4: Block local/tmp/noop in prod path**  
  Evidence: LocalMediaStorage default (engines/media_v2/service.py:84-102); RAW_BUCKET deferred (engines/nexus/raw_storage/repository.py:38-72); Nexus noop (engines/nexus/backends/__init__.py:8-24); chat bus localhost defaults (engines/chat/service/transport_layer.py:65-82).  
  Files: media_v2/service.py, nexus/raw_storage/repository.py, nexus/backends/__init__.py, chat/service/transport_layer.py.  
  Invariants: Production rejects LocalMediaStorage/noop/RAW_BUCKET missing/localhost Redis; allow test-only bypass via explicit test flag or injected stub.  
  Verify: P0-CLOSE-A2 and raw-storage test.
- **P0-CLOSE-B5: Backend switch plumbing**  
  Evidence: No registry or switch test.  
  Files: registry + one service wiring (e.g., feature_flags) to observe switch.  
  Invariants: Service reads backend config dynamically; change in registry reflects on next call without redeploy.  
  Verify: P0-CLOSE-A3.
