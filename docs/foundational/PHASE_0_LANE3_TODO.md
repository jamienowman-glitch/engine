# Phase 0 — Lane 3 TODOs (Routing Registry & Real Infra by Default)

Context: Mounted surface area in `create_app` (engines/chat/service/server.py:68-118) must run only on durable backends; current env-driven defaults fall back to memory/noop across many services (e.g., feature flags backend env default memory at engines/feature_flags/repository.py:54-83, strategy locks at engines/strategy_lock/state.py:8-16, KPI at engines/kpi/service.py:13-20, budget at engines/budget/repository.py:175-182, maybes at engines/maybes/repository.py:88-97, memory at engines/memory/repository.py:104-111, analytics_events at engines/analytics_events/service.py:22-29, rate_limit at engines/nexus/hardening/rate_limit.py:78-85, firearms at engines/firearms/repository.py:117-124, page_content at engines/page_content/service.py:21-28, seo at engines/seo/service.py:11-18, realtime registry at engines/realtime/isolation.py:99-106, chat bus at engines/chat/service/transport_layer.py:65-82, Nexus backend allows noop at engines/nexus/backends/__init__.py:8-24, media_v2/raw_storage rely on RAW_BUCKET env at engines/media_v2/service.py:55-80 and engines/nexus/raw_storage/repository.py:38-72).

## TODOs (Lane 3, stable IDs)

1) **P0-C1 — Build Routing Registry (control-plane data)**
   - Files: new engines/routing/registry.py (interface + Firestore impl), engines/routing/tests/test_registry.py, engines/config/runtime_config.py (wiring hook only), engines/common/selecta.py (read-only hook for registry metadata if reused), docs if needed.
   - Change type: schema + repository + validation; no business logic changes to services yet.
   - Definition of verified: `python -m pytest engines/routing/tests/test_registry.py` proves CRUD and fail-fast on missing resource_kind (tenant/env/project aware).
   - Safety: Do NOT change service behaviors; registry API only.

2) **P0-C2 — Wire mounted services to registry (remove env/memory/noop defaults)**
   - Files: engines/feature_flags/repository.py, engines/strategy_lock/state.py, engines/kpi/service.py, engines/budget/repository.py, engines/maybes/repository.py, engines/memory/repository.py, engines/analytics_events/service.py, engines/nexus/hardening/rate_limit.py, engines/firearms/repository.py, engines/page_content/service.py, engines/seo/service.py, engines/realtime/isolation.py, engines/chat/service/transport_layer.py, engines/nexus/backends/__init__.py, engines/media_v2/service.py, engines/nexus/raw_storage/repository.py, engines/video_timeline/service.py (default repo fallback at engines/video_timeline/service.py:436-445), plus shared registry lookup utility.
   - Change type: replace env-based backend selection with registry lookup; enforce fail-fast when registry entry missing; adjust tests accordingly.
   - Definition of verified: 
     - `python -m pytest tests/test_real_infra_enforcement.py` (new) covers startup failure when registry lacks entries for mounted services.
     - `python -m pytest tests/test_routing_backend_switch.py` shows backend swap via registry data without redeploy.
     - Service-specific existing/added tests (e.g., `python -m pytest engines/feature_flags/tests -q`, `python -m pytest engines/realtime/tests -q`) updated to inject registry configs.
   - Safety: Do NOT change business logic of repositories/services; only backend selection/wiring. Keep test injection hooks (`set_*` functions) for unit tests.

3) **P0-C3 — Startup validation & error clarity**
   - Files: engines/chat/service/server.py (startup hook), engines/routing/registry.py (validation helpers), engines/chat/tests/test_startup_routing_validation.py.
   - Change type: add startup check to ensure required resource_kinds exist for all mounted routers (feature_flags, strategy_lock, budget, kpi, maybes, memory, analytics_events, rate_limit, firearms, page_content, seo, realtime registry, chat bus, nexus backend, media_v2 storage, raw_storage, timeline) and raise explicit 500/ConfigMissing.
   - Definition of verified: `python -m pytest engines/chat/tests/test_startup_routing_validation.py` fails when registry missing entries; passes when seeded; ensures CHAT_BUS_BACKEND redis config present (engines/chat/service/transport_layer.py:65-82) and REALTIME_REGISTRY_BACKEND durable (engines/realtime/isolation.py:99-106).
   - Safety: Validation only; no change to route handlers.

4) **P0-F1 — Remove local/tmp/Noop from production path**
   - Files: engines/nexus/backends/__init__.py (block noop), engines/media_v2/service.py (disallow LocalMediaStorage except explicit test flag), engines/nexus/raw_storage/repository.py (fail-fast if RAW_BUCKET missing instead of deferred), engines/chat/service/transport_layer.py (disallow localhost defaults unless registry supplies), engines/realtime/isolation.py (disallow InMemory default in prod path), engines/video_timeline/service.py (InMemory fallback allowed only in tests).
   - Change type: guardrails and test gating; no business logic modification.
   - Definition of verified: `python -m pytest tests/test_real_infra_enforcement.py` and `python -m pytest engines/nexus/raw_storage/tests/test_raw_storage.py::test_missing_bucket_raises` cover failure paths; integration smoke ensures LocalMediaStorage not used without explicit test flag.
   - Safety: Keep test-only paths via explicit test configuration; do not alter functional outputs beyond backend selection enforcement.

5) **P0-C4 — Backend switch demonstration (data-driven)**
   - Files: tests/test_routing_backend_switch.py, minimal fixture seeding registry for two backends (e.g., feature_flags memory vs firestore or rate_limit memory vs firestore).
   - Change type: test + fixture; no production code changes beyond registry usage added in P0-C2.
   - Definition of verified: `python -m pytest tests/test_routing_backend_switch.py` shows running app switches backend after registry update without redeploy.
   - Safety: Test-only; do not modify runtime behavior beyond using registry.

All TODOs: explicitly “do NOT change business logic”; only routing/selection/validation/backing store choice.
