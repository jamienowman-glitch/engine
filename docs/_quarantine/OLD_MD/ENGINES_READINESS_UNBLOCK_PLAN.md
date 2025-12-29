How to use this doc: Assign lanes to separate engineers, execute each TODO exactly as written (no scope creep), run the VTE commands verbatim to produce evidence, and mark Done only when the stated verification passes. This is a minimal unblock plan—not a redesign.

**TODO LANES**

**LANE 1**
- TODO ID: L1-T1  
  Blocker it resolves: “thread/canvas registry wiring vs verify_thread_access rejection”  
  Fix scope: ✅ minimal  
  Code pointers: engines/chat/service/http_transport.py::create_thread; engines/realtime/isolation.py::register_thread_resource  
  Exact change: After creating a thread in `create_thread`, call `register_thread_resource(ctx.tenant_id, thread.id)` so every new thread is registered before WS/SSE access checks.  
  Done means: Creating a thread via HTTP automatically registers it to the realtime registry for that tenant.  
  Verification (VTE required):  
  ```
  date -u
  echo "RUN_TOKEN=$(date -u +%Y%m%dT%H%M%SZ)-$RANDOM"
  git rev-parse HEAD
  git status --porcelain
  pytest engines/chat/tests/test_http_thread_registry.py -q
  echo $?
  ```
  (New test asserts registry contains the thread after POST /chat/threads with auth headers.)

- TODO ID: L1-T2  
  Blocker it resolves: “canvas_stream router not mounted; feature_flags router not mounted (prove entrypoint mounts)”  
  Fix scope: ✅ minimal  
  Code pointers: engines/chat/service/server.py::create_app; engines/canvas_stream/router.py::router; engines/feature_flags/routes.py::router  
  Exact change: Include `canvas_stream.router` and `feature_flags.routes.router` in `create_app()` with tags preserved.  
  Done means: `/sse/canvas/{canvas_id}` and `/feature-flags` routes are reachable in the main app.  
  Verification (VTE required):  
  ```
  date -u
  echo "RUN_TOKEN=$(date -u +%Y%m%dT%H%M%SZ)-$RANDOM"
  git rev-parse HEAD
  git status --porcelain
  pytest engines/chat/tests/test_server_mounts.py::test_canvas_and_feature_flags_mounted -q
  echo $?
  ```
  (Test spins FastAPI TestClient on create_app and asserts 403/401 from dependency chain instead of 404 on both routes.)

- TODO ID: L1-T3  
  Blocker it resolves: “thread/canvas registry wiring vs verify_thread_access rejection” (canvas side)  
  Fix scope: ✅ minimal  
  Code pointers: engines/canvas_stream/service.py::publish_canvas_event/subscribe_canvas; engines/realtime/isolation.py::register_canvas_resource  
  Exact change: On first publish/subscribe for a canvas_id, register it via `register_canvas_resource(tenant_id, canvas_id)` so `verify_canvas_access` passes.  
  Done means: Canvas SSE can stream after first event without manual registry seeding.  
  Verification (VTE required):  
  ```
  date -u
  echo "RUN_TOKEN=$(date -u +%Y%m%dT%H%M%SZ)-$RANDOM"
  git rev-parse HEAD
  git status --porcelain
  pytest engines/canvas_stream/tests/test_sse_rail.py::test_stream_canvas_auto_registers -q
  echo $?
  ```
  (New/updated test asserts stream endpoint returns 200 instead of 404 when headers/auth provided.)

- TODO ID: L1-A4
  Blocker it resolves: Multi-node / multi-process realtime (Chat Bus is in-memory only)
  Fix scope: ⚠️ moderate
  Code pointers: engines/chat/service/transport_layer.py::<bus|InMemoryBus> and add new file engines/chat/service/redis_transport.py::RedisBus
  Exact change: Implement RedisBus (redis-py) adhering to the existing bus protocol. Update transport_layer.py to instantiate RedisBus when CHAT_BUS_BACKEND=redis, else default to InMemoryBus.
  Done means: Setting CHAT_BUS_BACKEND=redis enables cross-process message passing for chat.
  Verification (VTE required):
  ```
  date -u
  echo "RUN_TOKEN=$(date -u +%Y%m%dT%H%M%SZ)-$RANDOM"
  git rev-parse HEAD
  git status --porcelain
  python3 -m pytest engines/chat/tests/test_redis_transport.py -q
  echo $?
  ```

**LANE 2**
- TODO ID: L2-T1  
  Blocker it resolves: “raw storage register_asset doesn’t persist metadata”  
  Fix scope: ⚠️ moderate  
  Code pointers: engines/nexus/raw_storage/service.py::register_asset; engines/nexus/raw_storage/repository.py::RawStorageRepository/S3RawStorageRepository  
  Exact change: Extend repository protocol with `persist_metadata(asset: RawAsset)`, implement InMemory persistence (new class) and no-op-safe stub in S3 repo; update `register_asset` to call `repo.persist_metadata(asset)` after building RawAsset.  
  Done means: Registering an asset records a retrievable RawAsset metadata entry (at least in-memory) in addition to returning the object.  
  Verification (VTE required):  
  ```
  date -u
  echo "RUN_TOKEN=$(date -u +%Y%m%dT%H%M%SZ)-$RANDOM"
  git rev-parse HEAD
  git status --porcelain
  pytest engines/nexus/raw_storage/tests/test_raw_storage.py::test_register_persists_metadata -q
  echo $?
  ```
  (New test uses InMemory repo to assert stored asset matches returned uri/ids.)

- TODO ID: L2-T2  
  Blocker it resolves: “media_v2 GET/list missing auth/context enforcement”  
  Fix scope: ✅ minimal  
  Code pointers: engines/media_v2/routes.py::get_media_asset/list_media_assets  
  Exact change: Add `Depends(get_request_context)` and `Depends(get_auth_context)` to GET/list routes and enforce `require_tenant_membership` + `assert_context_matches` with tenant_id param.  
  Done means: Unauthenticated or cross-tenant GET/list calls return 401/403; valid tenant succeeds.  
  Verification (VTE required):  
  ```
  date -u
  echo "RUN_TOKEN=$(date -u +%Y%m%dT%H%M%SZ)-$RANDOM"
  git rev-parse HEAD
  git status --porcelain
  pytest engines/media_v2/tests/test_media_v2_endpoints.py::test_get_requires_auth -q
  echo $?
  ```
  (New test asserts 401/403 without proper auth, 200 with correct headers.)

- TODO ID: L2-T3  
  Blocker it resolves: “GateChain budget/KPI defaults blocking (403) when unset”  
  Fix scope: ✅ minimal  
  Code pointers: engines/nexus/hardening/gate_chain.py::_enforce_budget/_enforce_kpi  
  Exact change: Allow missing budget/KPI config to pass when env is dev/staging or when env var `GATECHAIN_ALLOW_MISSING=1`; retain strict 403 in prod with no config.  
  Done means: GateChain.run no longer 403s by default in dev/staging when budgets/KPIs absent; prod remains strict.  
  Verification (VTE required):  
  ```
  date -u
  echo "RUN_TOKEN=$(date -u +%Y%m%dT%H%M%SZ)-$RANDOM"
  git rev-parse HEAD
  git status --porcelain
  GATECHAIN_ALLOW_MISSING=1 pytest engines/nexus/hardening/tests/test_prod_gates.py::test_gate_chain_allows_missing_when_flagged -q
  echo $?
  ```
  (New/updated test asserts GateChain.run succeeds in dev when flag set.)

**LANE 3**
- TODO ID: L3-T1  
  Blocker it resolves: “audit/logging backend hard dependency (Firestore/BigQuery) causing errors when not present”  
  Fix scope: ✅ minimal  
  Code pointers: engines/nexus/backends/__init__.py::get_backend; engines/logging/events/engine.py::run  
  Exact change: Wrap Firestore/BigQuery backend creation in try/except; on import/config failure fall back to InMemoryNexusBackend with a clear log, so `run` returns `accepted` instead of error when clients are missing.  
  Done means: DatasetEvent logging works in environments without GCP clients by falling back to in-memory backend.  
  Verification (VTE required):  
  ```
  date -u
  echo "RUN_TOKEN=$(date -u +%Y%m%dT%H%M%SZ)-$RANDOM"
  git rev-parse HEAD
  git status --porcelain
  pytest engines/nexus/tests/test_backends.py::test_get_backend_falls_back_without_firestore -q
  pytest engines/logging/tests/test_event_logging_fallback.py -q
  echo $?
  ```
  (Tests assert get_backend returns InMemory on missing Firestore and logging run returns status accepted.)

- TODO ID: L3-T2  
  Blocker it resolves: “canvas_stream router not mounted; feature_flags router not mounted” (audit/control plane proof)  
  Fix scope: ✅ minimal  
  Code pointers: engines/feature_flags/repository.py::FeatureFlagRepository (optional Firestore)  
  Exact change: No code change if Lane1 mounts; add minimal test proving `/feature-flags` responds (auth enforced).  
  Done means: Feature flags surface reachable through main app with auth dependencies, ready as control plane toggle.  
  Verification (VTE required):  
  ```
  date -u
  echo "RUN_TOKEN=$(date -u +%Y%m%dT%H%M%SZ)-$RANDOM"
  git rev-parse HEAD
  git status --porcelain
  pytest engines/chat/tests/test_server_mounts.py::test_feature_flags_requires_auth -q
  echo $?
  ```
  (Test checks 401/403 instead of 404.)

**GLOBAL READINESS GATE**
Commands that must pass for “ready enough to plug into core” after fixes:
```
date -u
echo "RUN_TOKEN=$(date -u +%Y%m%dT%H%M%SZ)-$RANDOM"
git rev-parse HEAD
git status --porcelain
pytest engines/chat/tests/test_http_thread_registry.py -q
pytest engines/chat/tests/test_server_mounts.py -q
pytest engines/canvas_stream/tests/test_sse_rail.py::test_stream_canvas_auto_registers -q
pytest engines/nexus/raw_storage/tests/test_raw_storage.py::test_register_persists_metadata -q
pytest engines/media_v2/tests/test_media_v2_endpoints.py::test_get_requires_auth -q
GATECHAIN_ALLOW_MISSING=1 pytest engines/nexus/hardening/tests/test_prod_gates.py::test_gate_chain_allows_missing_when_flagged -q
pytest engines/nexus/tests/test_backends.py::test_get_backend_falls_back_without_firestore -q
pytest engines/logging/tests/test_event_logging_fallback.py -q
python3 -m pytest engines/chat/tests/test_redis_transport.py -q
echo $?
```

**RISKS / OPEN QUESTIONS**
- Minimal raw storage persistence is in-memory; if core needs durable catalog, follow-up required to back by Firestore/S3 inventory.
- Vertex/Firestore dependencies for Vector Explorer remain; plan assumes environments without those either set NEXUS_BACKEND to memory or accept reduced capability.
- Registry auto-registration assumes thread/canvas creation paths are exercised before WS/SSE attach; if WS attaches to pre-existing IDs not created via Engines, need a seed call.
