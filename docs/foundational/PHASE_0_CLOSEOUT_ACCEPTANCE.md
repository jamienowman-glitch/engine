# Phase 0 Closeout Acceptance Gates (Ordered)

Copy/paste in order; gates map to TODO IDs in PHASE_0_CLOSEOUT_TODO.md.

1) **Registry CRUD + fail-fast** (P0-CLOSE-A1/B1)  
   - `python -m pytest engines/routing/tests/test_registry.py`

2) **Startup validation across mounted resource_kinds** (P0-CLOSE-A5/B3)  
   - `python -m pytest engines/chat/tests/test_startup_routing_validation.py`

3) **Real-infra enforcement (no memory/noop/local/tmp/localhost)** (P0-CLOSE-A2/B2/B4)  
   - `python -m pytest tests/test_real_infra_enforcement.py`

4) **Backend switch proof (data-driven)** (P0-CLOSE-A3/B5)  
   - `python -m pytest tests/test_routing_backend_switch.py`

5) **Project-required guard acceptance** (P0-CLOSE-A4)  
   - `python -m pytest engines/common/tests/test_request_context.py::test_project_required`

6) **Raw bucket fail-fast** (P0-CLOSE-A2/B4)  
   - `python -m pytest engines/nexus/raw_storage/tests/test_raw_storage.py::test_missing_bucket_raises`

7) **Realtime durability (Redis + registry durable)** (P0-CLOSE-A2/B2)  
   - `python -m pytest engines/chat/tests/test_realtime_durability.py`
