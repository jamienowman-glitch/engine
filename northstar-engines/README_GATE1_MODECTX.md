# Gate 1 Mode-only RequestContext Implementation

**Status**: ✅ STABILIZED & TESTED  
**Component**: ModeCTX (Mode-only RequestContext enforcement)  
**Scope**: G1-ModeCTX per PHASE_0_2_MASTER_TODO.md  

---

## Overview

This implementation provides a canonical, merge-friendly Mode-only RequestContext for Northstar Engines. It enforces strict mode validation (saas|enterprise|lab), rejects legacy env semantics, and provides unified context extraction for HTTP/SSE/WS transports.

**Key Property**: Single source of truth in `engines/common/identity.py` — no parallel modules, minimal merge conflict surface.

---

## Quick Start

### For HTTP Routes (FastAPI)
```python
from fastapi import Depends
from engines.common.identity import RequestContext, get_request_context

@app.post("/api/chat")
async def chat(ctx: RequestContext = Depends(get_request_context)):
    # ctx.tenant_id, ctx.mode, ctx.project_id guaranteed
    print(f"{ctx.mode}/{ctx.tenant_id}/{ctx.project_id}")
```

### For SSE/WS Transports
```python
from engines.common.identity import RequestContextBuilder

async def sse_handler(request: Request):
    try:
        ctx = RequestContextBuilder.from_request(request)
    except ValueError as e:
        return error_response(400, str(e))
```

### For Tests
```python
from engines.common.identity import RequestContextBuilder

headers = {
    "X-Mode": "lab",
    "X-Tenant-Id": "t_acme",
    "X-Project-Id": "proj_xyz"
}
ctx = RequestContextBuilder.from_headers(headers)
```

---

## File Structure

```
engines/
  ├─ __init__.py
  └─ common/
     ├─ __init__.py
     └─ identity.py (307 lines)
        ├─ RequestContext dataclass
        ├─ RequestContextBuilder class
        ├─ get_request_context() function
        └─ assert_context_matches() helper

tests/
  ├─ __init__.py
  └─ context/
     ├─ __init__.py
     └─ test_mode_headers.py (342 lines, 30+ tests)

docs/
  ├─ foundational/
  │  └─ PHASE_0_2_STATUS_UPDATE.md (Implementation status)
  └─ ModeCTX_Entrypoints.md (Integration guide)

conftest.py (Pytest config)
pytest.ini (Test discovery)
pyproject.toml (Project metadata)
MERGE_CHECKLIST.md (Merge strategy)
STABILIZATION_SUMMARY.md (This release summary)
verify_stabilization.py (Verification script)
```

---

## Header Contract

| Header | Required | Values | Fallback |
|--------|----------|--------|----------|
| X-Mode | ✅ Yes | saas \| enterprise \| lab | None (fail 400) |
| X-Tenant-Id | ✅ Yes | ^t_[a-z0-9_-]+$ | Query/Body |
| X-Project-Id | ✅ Yes | string | Query/Body |
| X-Request-Id | ⚠️ No | string | Auto-generate |
| X-Surface-Id | ⚠️ No | string | identity_repo |
| X-App-Id | ⚠️ No | string | identity_repo |
| X-User-Id | ⚠️ No | string | JWT |
| X-Membership-Role | ⚠️ No | string | JWT |
| **X-Env** | ❌ FORBIDDEN | — | Fail 400 |

---

## Design Highlights

### 1. Single Source of Truth
- **`engines/common/identity.py`** is the ONLY location
- No parallel identity modules anywhere in repo
- All transports use the same builder logic

### 2. Mode-Only Enforcement
- X-Mode header is REQUIRED (no fallback)
- Values MUST be: saas, enterprise, or lab
- Legacy env values (dev, staging, prod) are REJECTED
- No silent mode inference from environment

### 3. X-Env Rejection (Fail-Fast)
```python
# This fails immediately with ValueError
headers = {"X-Env": "staging", "X-Mode": "saas", ...}
ctx = RequestContextBuilder.from_headers(headers)  # ValueError!
```

### 4. Backward Compatibility
- JWT token decode: Via existing `default_jwt_service()`
- Identity repo defaults: Via existing `identity_repo`
- Query/body fallbacks: Still work (except env)
- FastAPI DI: No breaking changes
- Router wiring: Unchanged

### 5. Unified Context Extraction
All transports (HTTP/SSE/WS) use identical validation:
```
Request → RequestContextBuilder.from_request()
        ↓
    Header parsing (case-insensitive)
        ↓
    Mode validation (saas|enterprise|lab)
        ↓
    X-Env rejection (fail-fast)
        ↓
    Tenant/project validation
        ↓
    JWT overlay (if present)
        ↓
    RequestContext (guaranteed valid)
```

---

## Test Coverage

**File**: `tests/context/test_mode_headers.py`

**Test Classes**:
1. **TestRequestContextValidation** (7 tests)
   - Valid context creation
   - Missing/invalid tenant_id
   - Missing/invalid mode
   - Missing project_id

2. **TestRequestContextBuilderFromHeaders** (16 tests)
   - Minimal headers, case-insensitivity
   - Missing required headers
   - Invalid/legacy mode values
   - **X-Env rejection (case-insensitive)**
   - Optional header handling
   - JWT overlay
   - t_system tenant

3. **TestRequestContextBuilderFromRequest** (2 tests)
   - FastAPI Request integration
   - X-Env rejection via Request

4. **TestMinimalEndpoint** (5+ tests)
   - End-to-end validation
   - Valid/invalid request scenarios

**Total**: **30+ tests**, all passing ✅

---

## Contract Compliance (Gate 1 DoD)

| Requirement | Status | How |
|-------------|--------|-----|
| Mode-only (saas\|enterprise\|lab) | ✅ | RequestContext.__post_init__() validates |
| X-Mode header required | ✅ | get_request_context() + from_headers() |
| X-Env rejection | ✅ | _reject_env_header() + HTTPException 400 |
| Missing mode → 400 | ✅ | ValueError raised, caught as HTTPException 400 |
| Invalid mode → 400 | ✅ | Mode not in VALID_MODES → ValueError |
| Minimal endpoint pass | ✅ | TestMinimalEndpoint validates |
| HTTP/SSE/WS unified | ✅ | Same RequestContextBuilder.from_request() |
| Tenant + Project required | ✅ | X-Tenant-Id + X-Project-Id validation |
| No breaking changes | ✅ | JWT + identity_repo + DI unchanged |

---

## Integration Steps (For Your Team)

### Step 1: Verify Tests Pass
```bash
cd /Users/jaynowman/dev/northstar-engines/northstar-engines
python3 -m pytest tests/context/test_mode_headers.py -v
# Expected: 30+ tests PASSED ✅
```

### Step 2: Check Imports Work
```bash
python3 -c "from engines.common.identity import RequestContext, RequestContextBuilder, get_request_context"
# No error = ✅
```

### Step 3: Migrate One Route (Example)
```python
# OLD (before)
@app.post("/chat")
async def chat(x_tenant_id: str = Header(...), x_env: str = Header(None)):
    pass

# NEW (after)
@app.post("/chat")
async def chat(ctx: RequestContext = Depends(get_request_context)):
    x_tenant_id = ctx.tenant_id
    x_mode = ctx.mode  # Now REQUIRED and validated
```

### Step 4: Run Integration Tests
- Send request with valid headers (X-Mode, X-Tenant-Id, X-Project-Id)
- Verify response is correct
- Send request with X-Env header
- Verify 400 rejection

### Step 5: Merge (See MERGE_CHECKLIST.md)

---

## Error Handling

### Missing X-Mode
```
Status: 400 Bad Request
Body: {"detail": "X-Mode header is required; must be one of: saas, enterprise, lab"}
```

### Invalid X-Mode
```
Status: 400 Bad Request
Body: {"detail": "X-Mode must be one of frozenset({'saas', 'enterprise', 'lab'}), got: dev"}
```

### X-Env Header Present
```
Status: 400 Bad Request
Body: {"detail": "X-Env header is not allowed; use X-Mode (saas|enterprise|lab)"}
```

### Missing X-Tenant-Id
```
Status: 400 Bad Request
Body: {"detail": "X-Tenant-Id header is required"}
```

### Invalid Tenant Format
```
Status: 400 Bad Request
Body: {"detail": "tenant_id must match pattern ^t_[a-z0-9_-]+$, got: acme"}
```

---

## Backward Compatibility Guarantees

✅ **JWT Token Decode**
- Uses existing `engines.identity.jwt_service.default_jwt_service()`
- Token validation unchanged
- Tenant/user/role extraction preserved

✅ **Identity Repo Defaults**
- Uses existing `engines.identity.state.identity_repo`
- Surface/app defaults still applied
- No changes to repo interface

✅ **Query/Body Fallbacks**
- X-Tenant-Id can come from query or body
- X-Project-Id can come from query or body
- X-Surface-Id, X-App-Id, X-User-Id still supported
- **ONLY X-Env is forbidden** (no fallback)

✅ **FastAPI Dependency Injection**
- `get_request_context()` is a standard Depends() function
- Works with all FastAPI patterns
- No changes to DI mechanics

✅ **Router Wiring**
- No changes to route registration
- No changes to middleware
- No changes to exception handling (beyond 400 for invalid mode)

---

## Troubleshooting

### "ImportError: cannot import name RequestContext"
```python
# ✗ Wrong path
from engines.identity import RequestContext

# ✓ Correct path
from engines.common.identity import RequestContext
```

### "X-Mode must be one of... got: prod"
```
Client sent X-Mode: prod (legacy env value)
→ Must change to: saas, enterprise, or lab
```

### "X-Env header is not allowed"
```
Client sent X-Env header (legacy)
→ Must use X-Mode instead
```

### Tests fail with "ModuleNotFoundError"
```bash
# Ensure conftest.py sys.path is set correctly
cd /Users/jaynowman/dev/northstar-engines/northstar-engines
python3 -m pytest tests/context/test_mode_headers.py -v
```

---

## Next Steps (Lane A, Item 2)

After this Gate 1 merge, next is **Event Schemas**:
- Replace env with mode in DatasetEvent
- Add project_id, app_id, surface_id, run_id, step_id, schema_version, severity, storage_class
- Ensure emitters populate full scope
- File: `engines/dataset/events/schemas.py:9-32`

---

## Merge Checklist (Short Version)

- [x] All files created
- [x] All 30+ tests pass
- [x] No breaking changes
- [x] X-Env rejection works
- [x] Mode-only enforced
- [x] JWT/repo/DI unchanged
- [x] Documentation complete
- [x] Single source of truth
- [ ] Code review (pending)
- [ ] Merge to main (pending)

---

## Questions?

See:
- **MERGE_CHECKLIST.md** — Integration strategy + merge commands
- **ModeCTX_Entrypoints.md** — Import guide + migration examples
- **PHASE_0_2_STATUS_UPDATE.md** — Detailed implementation notes
- **STABILIZATION_SUMMARY.md** — Release notes

---

**Status**: ✅ READY FOR PRODUCTION  
**Confidence**: HIGH (30+ tests, 100% DoD, zero breaking changes)  
**Next**: Code review → Merge → Route migration

🚀
