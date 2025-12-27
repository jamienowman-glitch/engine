# Phase 0 Remaining TODO (Authoritative)

Each item is atomic, lane-tagged, and tied to acceptance verification. Secrets/Selecta/GSM/Stripe/Cognito remain deferred (Lane4).

## Lane3 — Routing Registry & Real Infra
- **T3.1 Implement routing registry + CRUD tests**  
  Evidence: No registry exists; services use env fallbacks (feature_flags env default memory at engines/feature_flags/repository.py:54-83; strategy_lock at engines/strategy_lock/state.py:8-16; budget at engines/budget/repository.py:175-182; memory at engines/memory/repository.py:104-111; realtime registry at engines/realtime/isolation.py:99-106; chat bus env at engines/chat/service/transport_layer.py:65-82; Nexus noop allowed at engines/nexus/backends/__init__.py:8-24; RAW_BUCKET env at engines/media_v2/service.py:55-80 and engines/nexus/raw_storage/repository.py:38-72).  
  Definition of Done: registry module exists (tenant/env/project aware), missing resource_kind raises, no env/memory/noop fallbacks reachable.  
  Verify: `python -m pytest engines/routing/tests/test_registry.py` and `python -m pytest tests/test_real_infra_enforcement.py`.

- **T3.2 Rewire mounted services to registry (remove env defaults)**  
  Evidence: Env selectors above plus timeline fallback (engines/video_timeline/service.py:436-445).  
  Definition of Done: feature_flags, strategy_lock, kpi, budget, maybes, memory, analytics_events, rate_limit, firearms, page_content, seo, realtime registry, chat bus, nexus backend, media_v2/raw_storage, timeline all fetch backend config from registry; missing config -> startup/runtime failure with clear error; tests updated.  
  Verify: `python -m pytest tests/test_real_infra_enforcement.py` and service-specific suites (e.g., `python -m pytest engines/feature_flags/tests -q`, `python -m pytest engines/realtime/tests -q`).

- **T3.3 Startup validation for routed services**  
  Evidence: create_app lacks registry checks (engines/chat/service/server.py:68-118).  
  Definition of Done: app startup fails fast if any required resource_kind missing or set to disallowed backend (noop/memory/local tmp); error message names resource_kind.  
  Verify: `python -m pytest engines/chat/tests/test_startup_routing_validation.py`.

- **T3.4 Block noop/local/tmp in prod path**  
  Evidence: LocalMediaStorage default (engines/media_v2/service.py:84-102); RAW_BUCKET deferred until use (engines/nexus/raw_storage/repository.py:38-72); Nexus noop backend allowed (engines/nexus/backends/__init__.py:8-24).  
  Definition of Done: production wiring rejects noop/local/tmp unless explicit test flag; RAW_BUCKET validated at startup; registry provides bucket/storage kind.  
  Verify: `python -m pytest engines/nexus/raw_storage/tests/test_raw_storage.py::test_missing_bucket_raises` and `python -m pytest tests/test_real_infra_enforcement.py`.

- **T3.5 Backend switch proof test**  
  Evidence: No `tests/test_routing_backend_switch.py`.  
  Definition of Done: test demonstrates backend change via registry data (no redeploy) for one mounted service (e.g., feature_flags or rate_limit).  
  Verify: `python -m pytest tests/test_routing_backend_switch.py`.

## Lane2 (acceptance gap only)
- **T2.1 Add project-required acceptance test**  
  Evidence: RequestContext requires project_id (engines/common/identity.py:22-115), but pytest target missing (`python3 -m pytest engines/common/tests/test_request_context.py::test_project_required` returned “not found”).  
  Definition of Done: test asserts 400 when project_id absent, 400/403 on mismatch, and success when provided; added to acceptance list.  
  Verify: `python -m pytest engines/common/tests/test_request_context.py::test_project_required`.

## Deferred Lane4 (secrets)
- Secrets/Selecta/GSM/Stripe/Cognito changes are explicitly out of Phase 0 scope; track separately when Lane4 opens.
