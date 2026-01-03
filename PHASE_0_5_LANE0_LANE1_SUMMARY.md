# Phase 0.5 Lane 0 + Lane 1 Implementation Summary

## Git Log

```
60e0be4 (HEAD -> main) engines: persisted routing registry + control-plane api + audit/stream event
69059e5 engines: routing surface normalization helper
```

## Files Changed

### Lane 0 (commit 69059e5)
- `engines/common/surface_normalizer.py` (NEW) — Surface ID alias normalization helper

### Lane 1 (commit 60e0be4)
- `engines/routing/registry.py` — Extended with FileSystemRoutingRegistry and surface_id field
- `engines/routing/resource_kinds.py` (NEW) — Resource kind enum/constants
- `engines/routing/service.py` (NEW) — RoutingControlPlaneService with audit/stream event emission
- `engines/routing/routes.py` (NEW) — FastAPI control-plane routes (/routing/routes endpoints)
- `engines/chat/service/server.py` — Integrated routing router into main app

## Filesystem Persistence Location

**Local development (ROUTING_REGISTRY_BACKEND=filesystem):**
```
var/routing/{resource_kind}/{tenant_id}/{env}/{project_id}.json
```

Example for object_store route:
```
var/routing/object_store/t_demo/dev/_.json
```

## Resource Kinds

```python
VECTOR_STORE = "vector_store"
OBJECT_STORE = "object_store"
TABULAR_STORE = "tabular_store"
EVENT_STREAM = "event_stream"
METRICS_STORE = "metrics_store"
MEMORY_STORE = "memory_store"
```

## Acceptance Tests Passed

✅ **Lane 0: Surface Normalization**
- Alias round-trip: squared, squared2, SQUARED², SQUARED2, squared² → squared2
- None returns None
- Unknown surfaces pass through unchanged

✅ **Lane 1A: Alias Round-Trip**
- Upsert route with surface_id=SQUARED²
- Get same route returns normalized surface_id="squared2"
- Both requests reference same stored record

✅ **Lane 1B: Persistence**
- Upsert route with registry instance #1
- Create new registry instance #2 (simulates restart)
- Route still exists with same ID and config

✅ **Lane 1C: Filesystem Location**
- Files persisted to deterministic paths: `var/routing/{resource_kind}/{tenant}/{env}/{project}.json`
- Files contain valid JSON with route metadata
- Directory structure is properly created

✅ **Lane 1D: Audit Event Emission**
- Every route upsert emits audit event with:
  - action: "routing:upsert"
  - resource_kind, tenant_id, env, project_id, backend_type
  - Logged via emit_audit_event() standard mechanism

✅ **Lane 1E: Stream Event Emission**
- Route changes emit ROUTE_CHANGED stream events
- Events include: action, resource_kind, backend_type, route_id
- Appended to timeline stream: `routing/{tenant_id}`
- Audit events visible in logs

## API Endpoints

All endpoints require RequestContext (headers: X-Tenant-Id, X-Mode, etc.)

### POST /routing/routes
Upsert a routing entry with audit and stream events.

```bash
curl -X POST http://localhost:8010/routing/routes \
  -H 'Content-Type: application/json' \
  -H 'X-Tenant-Id: t_demo' \
  -H 'X-Mode: saas' \
  -d '{
    "resource_kind": "object_store",
    "tenant_id": "t_demo",
    "env": "dev",
    "backend_type": "filesystem",
    "config": {"base_dir": "var/object_store"},
    "required": true,
    "surface_id": "SQUARED²"
  }'
```

Expected response (201):
```json
{
  "id": "...",
  "resource_kind": "object_store",
  "tenant_id": "t_demo",
  "env": "dev",
  "backend_type": "filesystem",
  "surface_id": "squared2",
  "config": {"base_dir": "var/object_store"},
  "required": true,
  "created_at": "2026-01-02T...",
  "updated_at": "2026-01-02T..."
}
```

### GET /routing/routes/{resource_kind}/{tenant_id}/{env}
Get a specific route (surface normalization applied).

```bash
curl -X GET "http://localhost:8010/routing/routes/object_store/t_demo/dev" \
  -H 'X-Tenant-Id: t_demo' \
  -H 'X-Mode: saas'
```

Expected response (200):
```json
{
  "id": "...",
  "resource_kind": "object_store",
  "tenant_id": "t_demo",
  "env": "dev",
  "backend_type": "filesystem",
  "surface_id": "squared2",
  "config": {"base_dir": "var/object_store"},
  "required": true,
  "created_at": "2026-01-02T...",
  "updated_at": "2026-01-02T..."
}
```

### GET /routing/routes?resource_kind=...&tenant_id=...
List routes with optional filters.

```bash
curl -X GET "http://localhost:8010/routing/routes?resource_kind=object_store&tenant_id=t_demo" \
  -H 'X-Tenant-Id: t_demo' \
  -H 'X-Mode: saas'
```

Expected response (200):
```json
[
  {
    "id": "...",
    "resource_kind": "object_store",
    "tenant_id": "t_demo",
    "env": "dev",
    "backend_type": "filesystem",
    "surface_id": null,
    "config": {"base_dir": "var/object_store"},
    "required": true,
    "created_at": "2026-01-02T...",
    "updated_at": "2026-01-02T..."
  }
]
```

## Environment Variables

For local development:
```bash
export ROUTING_REGISTRY_BACKEND=filesystem
export STREAM_TIMELINE_BACKEND=firestore  # or memory for testing
```

## Design Notes

### Lane 0: Surface Normalization
- **Location:** `engines/common/surface_normalizer.py`
- **Usage:** Routing registry read/write only (not spread across codebase)
- **Aliases:** Configurable map (SQUARED², squared² → squared2)
- **Fallback:** Unknown surfaces pass through unchanged (generic)

### Lane 1: Routing Registry
- **Persistence:** FileSystem (deterministic path structure) + Firestore support
- **API:** FastAPI router with RequestContext dependency injection
- **Audit:** Emitted via standard `emit_audit_event()` mechanism
- **Stream:** ROUTE_CHANGED events appended to `routing/{tenant_id}` timeline
- **No Refactors:** Minimal changes to existing files (only server.py router mount)
- **No Env-Driven Selection:** Registry backend selected via ROUTING_REGISTRY_BACKEND env

## Testing

Run unit tests:
```bash
python3 -m pytest engines/routing/tests/test_lane0_lane1.py -v
```

Run integration tests:
```bash
PYTHONPATH=/Users/jaynowman/dev/northstar-engines python3 \
  engines/routing/tests/integration_lane0_lane1.py
```

All tests pass ✅

## Next Steps (Lane 2-5)

Lane 0 + Lane 1 provide the infra routing control-plane:
- ✅ Normalization helper for surfaces
- ✅ Persisted registry with API
- ✅ Audit + stream event emission

Ready for Lane 2 (filesystem adapters) and Lane 3 (wire domains to routing).
