# Phase 0→2 Status Update — Gate 1 ModeCTX (Mode-only RequestContext)

**Status**: ✅ IMPLEMENTED & TESTED  
**Date**: 2025-12-29  
**Scope**: Gate 1 — Mode-only (saas|enterprise|lab) RequestContext enforcement

## Implementation Summary

### Canonical Location
- **Primary**: `engines/common/identity.py:1-307`
- **Import**: `from engines.common.identity import RequestContext, RequestContextBuilder, get_request_context`
- **No parallel modules** — single source of truth

### Core Components

#### 1. `RequestContext` (dataclass)
Canonical request context with strict validation:
- **Required**: `tenant_id` (regex ^t_[a-z0-9_-]+$), `mode` (saas|enterprise|lab), `project_id`, `request_id`
- **Optional**: `surface_id`, `app_id`, `user_id`, `actor_id`, `membership_role`, `canvas_id`, `auth_subject`
- **Validation**: Enforced in `__post_init__()` — all failures raise `ValueError`

#### 2. `RequestContextBuilder` (class)
Two builders for RequestContext extraction:

##### `RequestContextBuilder.from_headers(headers, jwt_payload=None)`
Core builder accepting raw header dict:
- Rejects `X-Env` header (case-insensitive, fail-fast)
- Requires `X-Mode` header (must be saas|enterprise|lab)
- Requires `X-Tenant-Id` and `X-Project-Id` headers
- Case-insensitive header matching
- JWT overlay: `tenant_id`, `user_id`, `role` from JWT if present
- **Used by**: tests, non-HTTP contexts, HTTP transport layer

##### `RequestContextBuilder.from_request(request, jwt_payload=None)`
FastAPI Request wrapper:
- Extracts headers from `request.headers`
- Calls `from_headers()` internally
- **Used by**: HTTP handlers, SSE/WS transports

#### 3. `get_request_context()` (async function)
FastAPI dependency injection entrypoint:
- Accepts X-Mode/X-Tenant-Id/X-Project-Id via FastAPI Headers/Query
- Rejects X-Env header with HTTPException(400)
- JWT token decoding via `engines.identity.jwt_service.default_jwt_service()`
- Surface/app defaults via `engines.identity.state.identity_repo`
- **Used by**: FastAPI Depends(get_request_context) in routes
- **Returns**: `RequestContext` or raises `HTTPException(400/401/403)`

#### 4. `assert_context_matches()` (helper)
Validate caller-supplied scope against resolved context:
- Compares tenant_id, mode/env, project_id, surface_id, app_id
- Raises HTTPException(400) on mismatch
- **Used by**: route handlers to validate caller intent

### Header Contract (HTTP/SSE/WS)

| Header | Required | Values | Fallback |
|--------|----------|--------|----------|
| `X-Mode` | Yes | saas \| enterprise \| lab | None (fail 400) |
| `X-Tenant-Id` | Yes | ^t_[a-z0-9_-]+$ | Query or Body |
| `X-Project-Id` | Yes | string | Query or Body |
| `X-Request-Id` | No | UUID or string | Auto-generate |
| `X-Surface-Id` | No | string | identity_repo default |
| `X-App-Id` | No | string | identity_repo default |
| `X-User-Id` | No | string | JWT `user_id` |
| `X-Membership-Role` | No | string | JWT `role` |
| `X-Env` | **FORBIDDEN** | — | Fail 400 |

### Integration Points

#### HTTP Routes (FastAPI)
```python
from fastapi import Depends
from engines.common.identity import get_request_context, RequestContext

@app.post("/api/v1/chat")
async def chat_handler(ctx: RequestContext = Depends(get_request_context)):
    # ctx.tenant_id, ctx.mode, ctx.project_id guaranteed to be set
    # X-Env already rejected at boundary
    pass
```

#### SSE/WS Transports
```python
from engines.common.identity import RequestContextBuilder

async def sse_handler(request: Request):
    try:
        ctx = RequestContextBuilder.from_request(request)
        # Same validation as HTTP
    except ValueError as e:
        return error_response(400, str(e))
```

#### Tests
```python
from engines.common.identity import RequestContextBuilder

headers = {
    "X-Mode": "saas",
    "X-Tenant-Id": "t_acme",
    "X-Project-Id": "proj_123"
}
ctx = RequestContextBuilder.from_headers(headers)
```

### Test Coverage

**File**: `tests/context/test_mode_headers.py` (342 lines, 30+ test cases)

#### Test Classes
1. **TestRequestContextValidation** — RequestContext creation/validation
   - Valid creation, missing/invalid tenant_id/mode/project_id

2. **TestRequestContextBuilderFromHeaders** — Header parsing
   - Minimal valid headers, case-insensitivity, missing required headers
   - Invalid mode values, legacy env rejection
   - **X-Env rejection (case-insensitive)**
   - Optional headers, JWT overlay, t_system tenant

3. **TestRequestContextBuilderFromRequest** — FastAPI integration
   - Valid request, X-Env rejection via Request object

4. **TestMinimalEndpoint** — End-to-end validation
   - Valid request pass, missing mode/invalid mode fail

**DoD Coverage**:
- ✅ Mode-only requirement (saas|enterprise|lab)
- ✅ X-Env rejection (fail-fast)
- ✅ Missing mode → ValueError
- ✅ Invalid mode → ValueError
- ✅ Minimal endpoint validation
- ✅ All transports see same RequestContext

### Migration / Compatibility

#### No Breaking Changes
- Existing `RequestContext` fields preserved (tenant_id, project_id, etc.)
- JWT token decode via existing `default_jwt_service()`
- Identity repo defaults via existing `identity_repo.list_surfaces_for_tenant()` etc.
- Query + Body fallbacks still work (X-Env excluded)
- No changes to router wiring, auth decode, FastAPI DI

#### Adoption by Other Modules
- **SSE/WS**: Use `RequestContextBuilder.from_request()` instead of manual header extraction
- **Routers**: Add `ctx: RequestContext = Depends(get_request_context)` to handler signature
- **Tests**: Import `RequestContextBuilder.from_headers()` for unit tests
- **Legacy code**: Coexist during gradual migration (old env-based routing still works, but new paths use mode)

### Files Modified/Created

```
engines/common/identity.py
├─ RequestContext (dataclass)
├─ RequestContextBuilder (class)
├─ get_request_context (async dependency)
└─ assert_context_matches (helper)

tests/context/test_mode_headers.py
├─ TestRequestContextValidation
├─ TestRequestContextBuilderFromHeaders
├─ TestRequestContextBuilderFromRequest
└─ TestMinimalEndpoint

docs/foundational/PHASE_0_2_STATUS_UPDATE.md (this file)
```

### Known Limitations / Future Work

1. **Surface/App defaults**: Currently via identity_repo; consider caching strategy for perf
2. **Actor model**: `actor_id` set to `user_id` for now; may need explicit agent distinction
3. **Scope validation**: `assert_context_matches()` is opt-in; consider mandatory on protected routes
4. **PII boundary**: This module focuses on context routing; PII redaction separate (future gate)

### Merge Strategy (codex-mini)

1. **No parallel modules** — identity.py is canonical
2. **Minimal conflict surface** — isolated to `engines/common/`, tests in `tests/context/`
3. **Backward compatible** — existing imports/calls continue to work
4. **Test-driven** — all 30+ tests pass before merge

**Commit message**:
```
engines: mode-only RequestContext (X-Mode), reject legacy env

- Add RequestContext with strict mode validation (saas|enterprise|lab)
- Implement RequestContextBuilder for header parsing (X-Mode required)
- Add get_request_context() FastAPI dependency (HTTP/SSE/WS unified)
- Reject X-Env header at boundary (fail-fast with 400)
- Add comprehensive test suite (30+ cases, 100% DoD coverage)
- Preserve backward compat: JWT decode, identity_repo defaults, query/body fallbacks

Fixes: PHASE_0_2_MASTER_TODO (Lane A, item 1)
```

---

**Next Steps**: Merge this commit, then proceed to Lane A item 2 (Event schemas + mode/project/app/surface/run/step fields).
