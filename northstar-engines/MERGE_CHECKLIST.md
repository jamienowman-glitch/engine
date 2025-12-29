# Gate 1 ModeCTX — Merge Checklist for codex-mini

## Pre-Merge Verification

### ✅ File Structure (No Conflicts)
```
engines/
  common/
    __init__.py
    identity.py          ← CANONICAL RequestContext + RequestContextBuilder

tests/
  context/
    __init__.py
    test_mode_headers.py ← Comprehensive test suite (30+ cases)

docs/
  foundational/
    PHASE_0_2_STATUS_UPDATE.md      ← Implementation status
  ModeCTX_Entrypoints.md             ← Integration guide

conftest.py              ← Pytest config (fixed sys.path)
pytest.ini               ← Test discovery config
pyproject.toml           ← Project metadata + test deps
run_tests.py             ← Test runner script
```

### ✅ No Parallel Modules
- Single source of truth: `engines/common/identity.py`
- No duplicate identity.py in other locations
- No forked RequestContext implementations

### ✅ Backward Compatibility Preserved
- **JWT decode**: Via existing `engines.identity.jwt_service.default_jwt_service()`
- **Identity repo defaults**: Via existing `engines.identity.state.identity_repo`
- **Router wiring**: No changes to FastAPI route registration
- **FastAPI DI**: Existing dependency injection patterns work unchanged
- **Header casing**: Case-insensitive header matching (HTTP spec compliant)

---

## Integration Checklist (For Your Codebase)

### 1. Verify No Import Conflicts
```bash
# Check that your existing imports still work
grep -r "from engines.common.identity import" . --include="*.py"
# Should show only new test imports + your new routes (if using ModeCTX)
```

### 2. Verify Tests Pass
```bash
cd /Users/jaynowman/dev/northstar-engines/northstar-engines
pytest tests/context/test_mode_headers.py -v

# Expected: All tests pass
# Summary: 30+ passed in X.XXs
```

### 3. Update Existing Routes (gradual migration)
When migrating routes from old pattern to ModeCTX:

**Before** (Old pattern):
```python
from fastapi import Header
from engines.common.identity import RequestContext

@app.post("/chat")
async def chat(
    x_tenant_id: str = Header(...),
    x_env: str = Header(None),
    x_project_id: str = Header(...)
):
    # Manual header parsing
    pass
```

**After** (ModeCTX pattern):
```python
from fastapi import Depends
from engines.common.identity import RequestContext, get_request_context

@app.post("/chat")
async def chat(ctx: RequestContext = Depends(get_request_context)):
    # ctx.tenant_id, ctx.mode, ctx.project_id already validated
    pass
```

### 4. SSE/WS Transport Migration
If you have existing SSE/WS handlers:

**Before** (Old pattern):
```python
async def sse_handler(request: Request):
    headers = dict(request.headers)
    tenant_id = headers.get("X-Tenant-Id")
    env = headers.get("X-Env")
    # Manual validation
```

**After** (ModeCTX pattern):
```python
from engines.common.identity import RequestContextBuilder

async def sse_handler(request: Request):
    try:
        ctx = RequestContextBuilder.from_request(request)
        # ctx.tenant_id, ctx.mode, ctx.project_id validated
    except ValueError as e:
        return error_response(400, str(e))
```

---

## Conflict Resolution Strategy

### If You Have an Existing `engines/common/identity.py`
**Option A (Recommended)**: Merge both files
1. Keep existing functions/classes that don't conflict
2. Add new RequestContext/RequestContextBuilder from this PR
3. Ensure no duplicate definitions
4. Run tests to verify combined behavior

**Option B**: Replace with ModeCTX version
1. Back up your existing file
2. Use ModeCTX version as base
3. Reintegrate your custom functions if needed
4. Run tests

### If You Have Custom RequestContext
1. Compare with ModeCTX RequestContext dataclass
2. If fields conflict, discuss in PR
3. ModeCTX is canonical for Gate 1 (auth boundary)
4. Custom fields can be added as optional in separate module

### If You Have Custom identity.py Anywhere Else
1. Consolidate to `engines/common/identity.py`
2. No parallel identity modules allowed (contract freeze)
3. Coordinate with team on priority if conflicts

---

## Testing Strategy (Your Side)

### Unit Tests
```bash
# Run ModeCTX tests
pytest tests/context/test_mode_headers.py -v

# Run your existing identity tests (if any)
pytest tests/identity/ -v

# Run all tests together
pytest tests/ -v
```

### Integration Tests
1. Pick one existing route that uses headers
2. Migrate to `Depends(get_request_context)`
3. Send request with X-Mode/X-Tenant-Id/X-Project-Id headers
4. Verify response is correct
5. Verify X-Env rejection returns 400

### Edge Cases to Validate
```python
# Missing X-Mode → 400
curl -H "X-Tenant-Id: t_acme" -H "X-Project-Id: p1" http://localhost:8000/api

# Invalid X-Mode → 400
curl -H "X-Mode: dev" -H "X-Tenant-Id: t_acme" -H "X-Project-Id: p1" http://localhost:8000/api

# X-Env present → 400
curl -H "X-Env: prod" -H "X-Mode: saas" -H "X-Tenant-Id: t_acme" -H "X-Project-Id: p1" http://localhost:8000/api

# Valid request → 200
curl -H "X-Mode: saas" -H "X-Tenant-Id: t_acme" -H "X-Project-Id: p1" http://localhost:8000/api
```

---

## Rollback Plan (If Needed)

### Minimal Impact Rollback
1. Remove import of `get_request_context` from routes
2. Revert to manual header parsing (old pattern)
3. Keep `RequestContext` dataclass (non-breaking)
4. Delete test files if needed (won't affect prod code)

### Full Rollback
```bash
git revert <commit-sha>
# Or revert commit message + files

# Tests will need updating if they import ModeCTX
```

---

## Sign-Off Checklist

- [ ] No import conflicts with existing code
- [ ] Tests pass: `pytest tests/context/test_mode_headers.py -v`
- [ ] No parallel identity modules in repo
- [ ] Existing auth/JWT decode still works
- [ ] Existing router wiring unchanged
- [ ] FastAPI dependency injection still works
- [ ] Case-insensitive header matching verified
- [ ] X-Env rejection tested (400 on presence)
- [ ] At least one route migrated to ModeCTX (optional for first merge)
- [ ] Merge commit message references Gate 1 / PHASE_0_2_MASTER_TODO

---

## Merge Commit Message Template

```
engines: mode-only RequestContext (X-Mode), reject legacy env

[Gate 1 Implementation]

Core changes:
- Add RequestContext dataclass with strict mode validation (saas|enterprise|lab)
- Implement RequestContextBuilder for unified header parsing
  - from_headers(): raw dict (tests, transports)
  - from_request(): FastAPI Request wrapper
- Add get_request_context() FastAPI dependency (HTTP/SSE/WS unified)
- Reject X-Env header at boundary (fail-fast with HTTPException 400)

Backward compatibility:
- Preserve JWT token decode via default_jwt_service()
- Preserve identity_repo defaults (surface/app)
- Preserve query/body fallbacks (X-Env excluded)
- No changes to router wiring or auth flow

Testing:
- Add 30+ test cases covering all validation paths
- All tests pass: pytest tests/context/test_mode_headers.py -v

Documentation:
- PHASE_0_2_STATUS_UPDATE.md: implementation details
- ModeCTX_Entrypoints.md: integration guide for other modules

Fixes: PHASE_0_2_MASTER_TODO (Lane A, item 1 / G1-ModeCTX)
Relates-to: PHASE_0_2_CONTRACT_FREEZE_MODE_NO_INMEMORY.md
```

---

## Success Criteria (Definition of Done)

✅ **All 30+ tests pass**
```bash
pytest tests/context/test_mode_headers.py -v
# 30+ passed
```

✅ **No import conflicts**
```bash
python -c "from engines.common.identity import RequestContext, RequestContextBuilder, get_request_context; print('OK')"
```

✅ **X-Env rejection works**
```python
headers = {"X-Env": "prod", "X-Mode": "saas", "X-Tenant-Id": "t_acme", "X-Project-Id": "p1"}
try:
    RequestContextBuilder.from_headers(headers)
except ValueError as e:
    assert "X-Env" in str(e)  # ✅ Pass
```

✅ **Mode-only requirement enforced**
```python
# Valid modes
for mode in ["saas", "enterprise", "lab"]:
    ctx = RequestContext(tenant_id="t_a", mode=mode, project_id="p1")

# Invalid modes reject
for mode in ["dev", "staging", "prod", "invalid"]:
    with pytest.raises(ValueError):
        RequestContext(tenant_id="t_a", mode=mode, project_id="p1")
```

✅ **Backward compat preserved**
- Existing routes still work (if not migrated)
- JWT decode untouched
- Identity repo defaults untouched
- No breaking changes to public APIs

---

**Ready for merge!** 🚀
