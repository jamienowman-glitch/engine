# Phase 0 — Lane 3 Resource Kind Map (Routing + Persistence)

| resource_kind | Current default behavior (evidence) | Target routing source | Must-be-durable backend(s) |
| --- | --- | --- | --- |
| feature_flags | Env `FEATURE_FLAGS_BACKEND` default `memory` (engines/feature_flags/repository.py:54-83) | Routing registry (tenant/env) | Firestore (or configured durable) |
| strategy_lock | Env `STRATEGY_LOCK_BACKEND` default InMemory (engines/strategy_lock/state.py:8-16) | Routing registry | Firestore |
| kpi | Env `KPI_BACKEND` default InMemory (engines/kpi/service.py:13-20) | Routing registry | Firestore |
| budget | Env `BUDGET_BACKEND` default InMemory (engines/budget/repository.py:175-182) | Routing registry | Firestore |
| maybes | Env `MAYBES_BACKEND` default InMemory (engines/maybes/repository.py:88-97) | Routing registry | Firestore |
| memory sessions/blackboard | Env `MEMORY_BACKEND` default InMemory (engines/memory/repository.py:104-111) | Routing registry | Firestore |
| analytics_events | Env `ANALYTICS_EVENTS_BACKEND` default InMemory (engines/analytics_events/service.py:22-29) | Routing registry | Firestore |
| rate_limit | Env `RATE_LIMIT_BACKEND` default InMemory (engines/nexus/hardening/rate_limit.py:78-85) | Routing registry | Firestore |
| firearms | Env `FIREARMS_BACKEND` default InMemory (engines/firearms/repository.py:117-124) | Routing registry | Firestore |
| page_content | Env `PAGE_CONTENT_BACKEND` default InMemory (engines/page_content/service.py:21-28) | Routing registry | Firestore |
| seo | Env `SEO_BACKEND` default InMemory (engines/seo/service.py:11-18) | Routing registry | Firestore |
| realtime_registry | Env `REALTIME_REGISTRY_BACKEND` default InMemory (engines/realtime/isolation.py:99-106) | Routing registry | Firestore (or chosen durable) |
| chat_bus | Env `CHAT_BUS_BACKEND` default `memory` disallowed but still env-driven (engines/chat/service/transport_layer.py:65-82) | Routing registry | Redis (host/port via registry) |
| nexus_backend | Allows `noop` backend via env (engines/nexus/backends/__init__.py:8-24) | Routing registry | Firestore or BigQuery (no noop) |
| media_v2 storage | S3 storage requires RAW_BUCKET env; LocalMediaStorage is local tmp (engines/media_v2/service.py:55-101) | Routing registry provides bucket + storage kind | S3 (no local/tmp in prod) |
| raw_storage presign | S3RawStorageRepository defers RAW_BUCKET check to use (engines/nexus/raw_storage/repository.py:38-72) | Routing registry provides bucket | S3 with early validation |
| timeline projects/sequences | Firestore fallback to InMemory when Firestore fails (engines/video_timeline/service.py:436-445) | Routing registry selects repo | Firestore |
