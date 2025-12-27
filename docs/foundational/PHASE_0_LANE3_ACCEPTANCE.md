# Phase 0 — Lane 3 Acceptance Gates (Routing Registry & Real Infra)

Copy/paste commands to prove Lane 3:

1) **Routing registry CRUD + fail-fast**
   - `python -m pytest engines/routing/tests/test_registry.py`
   - Confirms registry read/write and MissingConfig raises.

2) **Startup validation across mounted routers**
   - `python -m pytest engines/chat/tests/test_startup_routing_validation.py`
   - Ensures create_app (engines/chat/service/server.py:68-118) fails without registry entries for feature_flags (engines/feature_flags/repository.py:54-83), strategy_lock (engines/strategy_lock/state.py:8-16), kpi (engines/kpi/service.py:13-20), budget (engines/budget/repository.py:175-182), maybes (engines/maybes/repository.py:88-97), memory (engines/memory/repository.py:104-111), analytics_events (engines/analytics_events/service.py:22-29), rate_limit (engines/nexus/hardening/rate_limit.py:78-85), firearms (engines/firearms/repository.py:117-124), page_content (engines/page_content/service.py:21-28), seo (engines/seo/service.py:11-18), realtime registry (engines/realtime/isolation.py:99-106), chat bus (engines/chat/service/transport_layer.py:65-82), nexus backend (engines/nexus/backends/__init__.py:8-24), media_v2/raw_storage buckets (engines/media_v2/service.py:55-80; engines/nexus/raw_storage/repository.py:38-72), timeline repo default (engines/video_timeline/service.py:436-445).

3) **Real infra enforcement (no memory/noop/local tmp)**
   - `python -m pytest tests/test_real_infra_enforcement.py`
   - Verifies production path rejects InMemory/Noop/LocalMediaStorage unless explicitly test-configured.

4) **Backend switch proof (data-driven)**
   - `python -m pytest tests/test_routing_backend_switch.py`
   - Seeds registry with backend A, exercises endpoint, updates registry to backend B, replays request without redeploy; asserts different backend used.

5) **Raw bucket fail-fast**
   - `python -m pytest engines/nexus/raw_storage/tests/test_raw_storage.py::test_missing_bucket_raises`
   - Confirms RAW_BUCKET requirement enforced (engines/nexus/raw_storage/repository.py:38-72).

6) **Chat bus + realtime registry durability checks**
   - `python -m pytest engines/chat/tests/test_realtime_durability.py`
   - Ensures CHAT_BUS_BACKEND=redis with host/port (engines/chat/service/transport_layer.py:65-82) and REALTIME_REGISTRY_BACKEND=firestore (engines/realtime/isolation.py:99-106) survive restart/replay.
