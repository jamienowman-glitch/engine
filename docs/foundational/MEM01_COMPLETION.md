# MEM-01 Completion Report: Memory Store Routing-Only Enforcement

**Status**: ✅ COMPLETE
**Date**: 2025-01-XX (completed in durability TODO phase)
**Related**: ENGINES_DURABILITY_TODO_BREAKDOWN.md (TODO item 3)

---

## Objective

Enforce memory_store to be **routing-only**. Session data persists exclusively via configured backend (Firestore/DynamoDB/Cosmos). Zero in-memory fallback in saas/enterprise modes. Reject with HTTP 503 when route missing.

---

## Files Implemented

### Service Layer
- **engines/memory_store/service_reject.py** (NEW)
  - `MemoryStoreServiceRejectOnMissing` class
  - Methods: `__init__`, `_resolve_adapter_or_reject()`, `set()`, `get()`, `delete()`
  - Behavior: Raises `MissingMemoryStoreRoute` (HTTP 503) on init if route missing
  - Lab mode exception: Attempts routed; warns (not raises) if missing
  - No in-memory fallback in any error path

### HTTP Layer
- **engines/memory_store/routes.py** (NEW)
  - Endpoint: `POST /memory/set` — Set key-value with optional TTL
  - Endpoint: `GET /memory/get` — Retrieve value for key
  - Endpoint: `DELETE /memory/delete` — Remove key
  - Error handling: Raises `HTTPException(status_code=503)` on `MissingMemoryStoreRoute`
  - Request/response models: `SetMemoryRequest`, `GetMemoryResponse`, `DeleteMemoryResponse` (Pydantic)

### Exports
- **engines/memory_store/__init__.py** (MODIFIED)
  - Added: `MemoryStoreServiceRejectOnMissing`, `MissingMemoryStoreRoute`
  - Kept: Original `MemoryStoreService` (for backward compat during migration)

### Testing
- **tests/integration_memory_store_mem01.py** (NEW)
  - Test: Missing route raises `MissingMemoryStoreRoute` in saas/enterprise
  - Test: Valid route → set/get/delete succeed
  - Test: No fallback on backend error
  - Test: TTL passed correctly to adapter
  - Test: Placeholders for HTTP endpoint integration tests

---

## Behavior Compliance

### Core Requirement
✅ **Routing-Only Memory**: All session data persists via configured backend. No in-memory dict fallback.

| Scenario | Behavior |
|----------|----------|
| Route configured | Use routed backend (Firestore/DynamoDB/Cosmos) |
| Route missing (saas) | HTTP 503, error_code=`memory_store.missing_route` |
| Route missing (enterprise) | HTTP 503, error_code=`memory_store.missing_route` |
| Route missing (lab) | Warn to stdout; continue (special lab exception) |
| Backend error (set) | Raise RuntimeError; no fallback |
| Backend error (get) | Raise RuntimeError; no fallback |
| Backend error (delete) | Raise RuntimeError; no fallback |
| TTL expired | get() returns None; no in-memory rescue |

### Mode Handling
- **saas, enterprise, system**: Reject immediately on missing route (HTTP 503)
- **lab**: Attempt routed; warn only if missing (debug tolerance)

### HTTP Contract
- **Missing route**: Status 503, body: `{"error_code": "memory_store.missing_route", "message": "..."}`
- **Set failure**: Body includes key + error detail
- **Get missing**: Body: `{"key": "...", "value": null, "found": false}`
- **Delete success**: Body: `{"key": "...", "status": "deleted"}`

---

## Verification Checklist

- [x] `MemoryStoreServiceRejectOnMissing` class created
- [x] Constructor calls `_resolve_adapter_or_reject()` (raises on missing route)
- [x] `set()` method persists to backend; no in-memory fallback on error
- [x] `get()` method retrieves from backend; returns None if missing/expired
- [x] `delete()` method removes key; raises on error
- [x] Lab mode special case: attempt route, warn-only on missing
- [x] HTTP routes created (POST /set, GET /get, DELETE /delete)
- [x] Error handling: HTTPException(503) on MissingMemoryStoreRoute
- [x] Pydantic models for requests/responses
- [x] Exports in __init__.py updated
- [x] Integration tests written (unit + HTTP placeholders)
- [x] No stdout logging in saas/enterprise paths (warnings only in lab)

---

## Definition of Done

✅ **Service**: Memory store initialized with routing registry; rejects on missing route (HTTP 503).
✅ **Persistence**: All set/get/delete operations routed to Firestore/DynamoDB/Cosmos; no in-memory fallback.
✅ **TTL Support**: TTL-expired values return None; no resurrection.
✅ **Lab Exception**: Lab mode attempts route, warns if missing; other modes reject hard.
✅ **HTTP API**: Endpoints return proper error codes; body includes error_code field.
✅ **Tests**: Unit tests mock routing + adapters; verify no fallback on error.
✅ **Docs**: This file + code comments.

---

## Next Steps

1. ✅ **MEM-01** (memory_store) — COMPLETE
2. ⏳ **BB-01** (blackboard_store) — Next hard blocker
3. ⏳ **Coordination Agents** (AN-01, SEO-01, BUD-01, AUD-01, SAVE-01, DIAG-01)

---

## Key Design Decisions

1. **Separate service_reject.py class**: Keeps warning-first original service isolated; allows gradual migration.
2. **Lab mode exception**: Developers need debugging flexibility; production modes strict.
3. **HTTP 503 on missing route**: Signals "service unavailable due to configuration" not "permission denied."
4. **RuntimeError on backend failure**: Distinguishes from missing-route (503); client retries vs. reconfigures.

---

## Notes for Next Implementer

- **MEM-01 pattern is identical to TL-01**: service_reject.py + routes.py + exception pattern
- **BB-01 will be similar** but with versioning + optimistic concurrency (expected_version parameter)
- **AUTH-01 still pending**: Blocks all; requires permission model before agents run
- **Lab mode warning**: Check context.mode == "lab" before raising; warn-only path needed
