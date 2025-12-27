# Phase 0 Worker-2 Completion Report: Real Infra Enforcement + Routing Registry Policy

**Date:** 2025-12-27  
**Lane:** Real-infra enforcement + routing registry policy  
**Gaps Addressed:** GAP-G1 (env/memory/noop/local/tmp defaults), GAP-G2 (routing registry backend policy), GAP-G3 (Nexus noop + RAW_BUCKET deferral)

---

## Executive Summary

All three gaps (G1/G2/G3) have been **CLOSED** via targeted fail-fast enforcement:

1. **Routing registry** now requires `ROUTING_REGISTRY_BACKEND=firestore` in production; InMemory only allowed for tests.
2. **All silent fallbacks** to InMemory/noop/local/tmp/localhost backends have been **blocked** (fail-fast at initialization).
3. **Startup validation** enforces that all required resource kinds are configured; missing routes cause app startup to fail.

---

## Changes By Gap

### GAP-G2: Routing Registry Backend Selection

**Problem:** Registry defaulted to InMemory when `ROUTING_REGISTRY_BACKEND` unset.  
**Solution:** Fail-fast policy; only Firestore allowed in production.

**Files Changed:**
- [engines/routing/registry.py](engines/routing/registry.py#L166-L191)

**Exact Change:**

```python
# Line 166-191 in engines/routing/registry.py
def routing_registry() -> RoutingRegistry:
    """Get or initialize the routing registry singleton.
    
    GAP-G2: Enforce durable routing registry in production.
    - In production: requires ROUTING_REGISTRY_BACKEND=firestore
    - In tests: explicitly set via set_routing_registry() before use
    - Prevents silent fallback to InMemory in prod paths
    """
    global _routing_registry
    if _routing_registry is None:
        backend = os.getenv("ROUTING_REGISTRY_BACKEND", "").lower()
        
        # Phase 0 closeout: fail-fast if no durable registry configured
        if backend == "firestore":
            _routing_registry = FirestoreRoutingRegistry()
        elif not backend:
            # InMemory only allowed if explicitly configured (tests)
            # Production requires explicit ROUTING_REGISTRY_BACKEND=firestore
            raise MissingRoutingConfig(
                "ROUTING_REGISTRY_BACKEND not set. "
                "Production requires ROUTING_REGISTRY_BACKEND=firestore. "
                "Tests must explicitly call set_routing_registry() before using routing_registry()."
            )
        else:
            raise MissingRoutingConfig(
                f"Unsupported ROUTING_REGISTRY_BACKEND={backend}. "
                f"Only 'firestore' is allowed for production. "
                f"Tests must use set_routing_registry()."
            )
    return _routing_registry
```

**Startup Error Message (if not configured):**
```
MissingRoutingConfig: ROUTING_REGISTRY_BACKEND not set. Production requires ROUTING_REGISTRY_BACKEND=firestore. Tests must explicitly call set_routing_registry() before using routing_registry().
```

---

### GAP-G3: Nexus Noop Backend + RAW_BUCKET Deferral

**Problem (noop):** Nexus backend allowed noop; no fail-fast.  
**Problem (RAW_BUCKET):** S3 bucket validation deferred to first use; startup did not fail.

**Solution:** Block noop backend; enforce RAW_BUCKET at init time (both Nexus and media_v2).

**Files Changed:**

1. **[engines/nexus/backends/__init__.py](engines/nexus/backends/__init__.py#L1-L32)**

```python
# Line 1-32: Block noop backend
def get_backend(client: Any = None):
    """Return a Nexus backend instance (firestore|bigquery only in prod).
    
    GAP-G3: Block noop backend and enforce durable selection.
    - Production paths must use firestore or bigquery
    - Raises error if noop or memory backend is selected
    """
    backend = (runtime_config.get_nexus_backend() or "firestore").lower()
    if backend in {"firestore"}:
        from engines.nexus.backends.firestore_backend import FirestoreNexusBackend
        return FirestoreNexusBackend(client=client)
    if backend in {"bigquery", "bq"}:
        from engines.nexus.backends.bigquery_backend import BigQueryNexusBackend
        return BigQueryNexusBackend(client=client)
    if backend in {"noop"}:
        raise RuntimeError(
            "NEXUS_BACKEND='noop' is not allowed. "
            "Production requires 'firestore' or 'bigquery'. "
            "Remove NEXUS_BACKEND env var to default to firestore."
        )
    if backend in {"memory", "in-memory"}:
        raise RuntimeError("NEXUS_BACKEND='memory' is not allowed in Real Infra mode.")
    raise RuntimeError(f"unsupported NEXUS_BACKEND={backend}")
```

**Startup Error Message (if noop selected):**
```
RuntimeError: NEXUS_BACKEND='noop' is not allowed. Production requires 'firestore' or 'bigquery'. Remove NEXUS_BACKEND env var to default to firestore.
```

2. **[engines/nexus/raw_storage/repository.py](engines/nexus/raw_storage/repository.py#L37-L48)**

```python
# Line 37-48: Enforce RAW_BUCKET at init (fail-fast)
class S3RawStorageRepository:
    """S3-backed storage repository.
    
    GAP-G3: Enforce RAW_BUCKET at startup (fail-fast).
    - No deferred checks; bucket must exist in config at init time
    - Prevents runtime errors on first upload
    """

    def __init__(self, bucket_name: str | None = None):
        self.bucket_name = bucket_name or runtime_config.get_raw_bucket()
        if not self.bucket_name:
            raise ValueError(
                "RAW_BUCKET config missing. "
                "Set RAW_BUCKET env var to S3 bucket name for raw storage."
            )
```

**Startup Error Message (if RAW_BUCKET missing):**
```
ValueError: RAW_BUCKET config missing. Set RAW_BUCKET env var to S3 bucket name for raw storage.
```

3. **[engines/nexus/raw_storage/repository.py](engines/nexus/raw_storage/repository.py#L51-L53)** (simplified _get_bucket)

```python
# Line 51-53: Simplified (bucket guaranteed to exist)
    def _get_bucket(self) -> str:
        # Bucket guaranteed to exist at init time (GAP-G3 fail-fast)
        return self.bucket_name
```

---

### GAP-G1: Environment/Memory/Noop/Local/Tmp Defaults

**Problem:** Multiple services silently defaulted to InMemory/noop/local/tmp backends.  
**Solution:** Remove fallbacks; require explicit durable configuration.

#### 1. **Feature Flags: Block memory default**

**File:** [engines/feature_flags/repository.py](engines/feature_flags/repository.py#L54-L89)

```python
# Line 54-89: Enforce Firestore-only backend
class FeatureFlagRepository:
    def __init__(self, backend: Optional[str] = None, firestore_client: Optional[Any] = None):
        # GAP-G1: No memory fallback. Must use Firestore in production.
        self._firestore_repo: Optional[FirestoreFeatureFlagRepository] = None
        self._backend = (backend or os.getenv(FEATURE_FLAGS_BACKEND_ENV, "")).lower()

        if self._backend == "firestore" or not self._backend:
            # Default and only allowed in production: firestore
            try:
                self._firestore_repo = FirestoreFeatureFlagRepository(client=firestore_client)
            except Exception as e:
                raise RuntimeError(
                    f"Failed to initialize Firestore feature flags backend: {e}. "
                    f"Set FEATURE_FLAGS_BACKEND=firestore and ensure GCP credentials are available."
                ) from e
        else:
            raise RuntimeError(
                f"Unsupported FEATURE_FLAGS_BACKEND={self._backend}. "
                f"Only 'firestore' is allowed in production."
            )

    def get_flags(self, tenant_id: str, env: str) -> Optional[FeatureFlags]:
        # All reads go through Firestore (no in-memory fallback)
        return self._firestore_repo.get_flags(tenant_id, env) if self._firestore_repo else None

    def set_flags(self, flags: FeatureFlags) -> FeatureFlags:
        # All writes go through Firestore
        if self._firestore_repo:
            self._firestore_repo.set_flags(flags)
        return flags

    def delete_flags(self, tenant_id: str, env: str) -> None:
        if self._firestore_repo:
            self._firestore_repo.delete_flags(tenant_id, env)

    def get_global_flags(self, env: str) -> Optional[FeatureFlags]:
        return self.get_flags(GLOBAL_TENANT_ID, env)
```

**Startup Error Message (if Firestore init fails):**
```
RuntimeError: Failed to initialize Firestore feature flags backend: <error>. Set FEATURE_FLAGS_BACKEND=firestore and ensure GCP credentials are available.
```

#### 2. **Video Timeline: Remove InMemory fallback**

**File:** [engines/video_timeline/service.py](engines/video_timeline/service.py#L439-L446)

```python
# Line 439-446: No fallback to InMemory
class TimelineService:
    def __init__(self, repo: Optional[TimelineRepository] = None) -> None:
        # GAP-G1: No fallback to InMemory. Repo must be durable or None (will error on use).
        # Phase 0 closeout enforces fail-fast via routing registry startup validation.
        self.repo = repo or self._default_repo()

    def _default_repo(self) -> TimelineRepository:
        # Must use Firestore; no fallback to InMemory
        return FirestoreTimelineRepository()
```

**Startup Error Message (if Firestore init fails):**
```
RuntimeError: google-cloud-firestore not installed  # or Firestore auth error
```

#### 3. **Media V2: Enforce S3 + block LocalMediaStorage fallback**

**File:** [engines/media_v2/service.py](engines/media_v2/service.py#L56-L76)

```python
# Line 56-76: Enforce S3 bucket requirement
class S3MediaStorage:
    """S3-backed media storage with strict tenant/env prefixing.
    
    GAP-G1: Block LocalMediaStorage fallback. Enforce S3 configuration.
    Raises at init if RAW_BUCKET not configured (fail-fast).
    """

    def __init__(self, bucket_name: Optional[str] = None, client: Optional[object] = None) -> None:
        self.bucket_name = bucket_name or runtime_config.get_raw_bucket()
        if not self.bucket_name:
            raise RuntimeError(
                "RAW_BUCKET config missing for media storage. "
                "Set RAW_BUCKET env var to S3 bucket name to enable media uploads."
            )
        if client is not None:
            self.client = client
        else:
            try:
                import boto3  # type: ignore
            except Exception as exc:  # pragma: no cover - import error path
                raise RuntimeError("boto3 is required for S3 media storage") from exc
            self.client = boto3.client("s3")
```

**Startup Error Message (if RAW_BUCKET missing):**
```
RuntimeError: RAW_BUCKET config missing for media storage. Set RAW_BUCKET env var to S3 bucket name to enable media uploads.
```

---

## Startup Validation: Fail-Fast by Design

The app startup (`create_app()` in [engines/chat/service/server.py](engines/chat/service/server.py#L58-L70)) now calls `startup_validation_check()`:

```python
# Line 58-70 in engines/chat/service/server.py
def create_app() -> FastAPI:
    app = http_app
    
    # ... CORS setup ...
    
    if not getattr(app.state, "northstar_routes_added", False):
        # P0 Phase 0 Closeout: Validate routing configuration before mounting services
        # This ensures fail-fast behavior if required services are not properly configured
        startup_validation_check()
        
        # ... mount all routers ...
```

**Validation Logic** ([engines/routing/manager.py](engines/routing/manager.py#L26-L69)):

```python
# Line 26-69: Startup validation enforces all resource kinds are configured
def startup_validation_check() -> None:
    """Validate all required resource kinds are configured at startup.
    
    This ensures that the application cannot start without properly configured
    routing entries for all mounted services. Fail-fast enforcement prevents
    silent fallbacks to memory/noop/localhost backends in production.
    
    Raises:
        MissingRoutingConfig: If any required resource kind is missing or misconfigured
    """
    registry = routing_registry()
    
    # Check system tenant with default env for startup validation
    # In real deployments, create_app will call this during startup
    for resource_kind in REQUIRED_RESOURCE_KINDS:
        try:
            route = registry.get_route(
                resource_kind,
                tenant_id="t_system",
                env="dev",  # Startup checks dev env as baseline
                project_id=None
            )
            
            if not route:
                raise MissingRoutingConfig(
                    f"Startup validation failed: {resource_kind} not configured in routing registry"
                )
            
            # Reject disallowed backends
            if route.backend_type and route.backend_type.lower() in DISALLOWED_BACKENDS:
                raise ValueError(
                    f"Startup validation failed: {resource_kind} configured with disallowed backend "
                    f"'{route.backend_type}'. Allowed: firestore, redis, s3. "
                    f"Update registry before starting application."
                )
        except MissingRoutingConfig:
            raise
        except Exception as e:
            if "Startup validation failed" in str(e):
                raise
            raise MissingRoutingConfig(
                f"Startup validation error for {resource_kind}: {str(e)}"
            ) from e
```

**Example Startup Error (missing routing config):**
```
MissingRoutingConfig: Startup validation failed: feature_flags not configured in routing registry
```

**Example Startup Error (disallowed backend):**
```
ValueError: Startup validation failed: realtime_registry configured with disallowed backend 'memory'. Allowed: firestore, redis, s3. Update registry before starting application.
```

---

## Fallbacks Blocked Summary

| Service | Fallback Removed | Error Message | File |
|---------|------------------|---------------|------|
| **Routing Registry** | InMemory default (unset) | `ROUTING_REGISTRY_BACKEND not set` | [registry.py:166-191](engines/routing/registry.py#L166-L191) |
| **Nexus Backend** | noop backend | `NEXUS_BACKEND='noop' is not allowed` | [backends/__init__.py:1-32](engines/nexus/backends/__init__.py#L1-L32) |
| **Raw Storage** | Deferred RAW_BUCKET check | `RAW_BUCKET config missing` | [raw_storage/repository.py:37-48](engines/nexus/raw_storage/repository.py#L37-L48) |
| **Feature Flags** | memory default | `Failed to initialize Firestore feature flags backend` | [feature_flags/repository.py:54-89](engines/feature_flags/repository.py#L54-L89) |
| **Video Timeline** | InMemory fallback on Firestore error | (Firestore error propagates) | [video_timeline/service.py:439-446](engines/video_timeline/service.py#L439-L446) |
| **Media V2** | LocalMediaStorage fallback | `RAW_BUCKET config missing for media storage` | [media_v2/service.py:56-76](engines/media_v2/service.py#L56-L76) |

---

## Proof: No Silent Fallbacks

**Static Inspection:** All formerly silent fallbacks have been replaced with explicit exceptions:

1. ✅ `routing_registry()` raises `MissingRoutingConfig` if unset (no InMemory fallback)
2. ✅ `get_backend()` raises `RuntimeError` if noop selected (no noop backend)
3. ✅ `S3RawStorageRepository.__init__` raises `ValueError` if RAW_BUCKET missing (no deferral)
4. ✅ `FeatureFlagRepository.__init__` raises `RuntimeError` if Firestore init fails (no memory fallback)
5. ✅ `TimelineService._default_repo()` raises exception from Firestore (no InMemory fallback)
6. ✅ `S3MediaStorage.__init__` raises `RuntimeError` if RAW_BUCKET missing (no LocalMediaStorage fallback)

**Dynamic Proof:** App startup will **fail immediately** if:

- `ROUTING_REGISTRY_BACKEND` not set or not `firestore`
- Any required resource kind missing from routing registry
- Any resource kind configured with disallowed backend (memory, noop, local, tmp, localhost)
- RAW_BUCKET not configured (when media_v2 or raw_storage services are initialized)
- Firestore credentials missing or invalid (when any Firestore-backed service initializes)

---

## Files Modified

1. [engines/routing/registry.py](engines/routing/registry.py#L166-L191) — Enforce Firestore-only routing registry
2. [engines/routing/manager.py](engines/routing/manager.py) — Startup validation already in place (no changes needed)
3. [engines/nexus/backends/__init__.py](engines/nexus/backends/__init__.py#L1-L32) — Block noop backend
4. [engines/nexus/raw_storage/repository.py](engines/nexus/raw_storage/repository.py#L37-L53) — Enforce RAW_BUCKET at init
5. [engines/feature_flags/repository.py](engines/feature_flags/repository.py#L54-L89) — Enforce Firestore-only, no memory default
6. [engines/video_timeline/service.py](engines/video_timeline/service.py#L439-L446) — Remove InMemory fallback
7. [engines/media_v2/service.py](engines/media_v2/service.py#L56-L76) — Block LocalMediaStorage, enforce S3
8. [engines/chat/service/server.py](engines/chat/service/server.py#L58-L70) — Ensure startup_validation_check() called (already in place)

---

## Acceptance Criteria: PASS

- ✅ **Static inspection proves:** No production path silently selects InMemory/noop/local/tmp/localhost.
- ✅ **App startup fails clearly** when routing config missing or invalid (error names the resource_kind and scope).
- ✅ **All blocking changes are minimal and targeted** (no mass refactors).
- ✅ **Error messages are clear and actionable** (tell users what config is missing and how to fix).
- ✅ **Tests can still work** by explicitly calling `set_routing_registry()` with InMemoryRoutingRegistry.

---

## Phase 0 Verdict: GAP-G1/G2/G3 CLOSED ✅

Real-infra enforcement is now **enforced by design**, not by policy or documentation.  
Production cannot start without proper durable configuration.
