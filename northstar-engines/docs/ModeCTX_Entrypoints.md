# ModeCTX Entrypoints Guide

## Quick Import Reference

### For HTTP/SSE/WS Routes (FastAPI)
```python
from fastapi import Depends
from engines.common.identity import get_request_context, RequestContext

@app.get("/api/endpoint")
async def my_handler(ctx: RequestContext = Depends(get_request_context)):
    print(f"Tenant: {ctx.tenant_id}, Mode: {ctx.mode}, Project: {ctx.project_id}")
```

### For Transport Layers (SSE/WS)
```python
from engines.common.identity import RequestContextBuilder

async def sse_handler(request: Request):
    try:
        ctx = RequestContextBuilder.from_request(request)
        # ctx is fully validated RequestContext
    except ValueError as e:
        return error_response(400, str(e))
```

### For Unit Tests
```python
from engines.common.identity import RequestContextBuilder

# Build context from headers dict
headers = {
    "X-Mode": "lab",
    "X-Tenant-Id": "t_acme",
    "X-Project-Id": "proj_123"
}
ctx = RequestContextBuilder.from_headers(headers)
assert ctx.mode == "lab"
```

### For Direct Context Creation (rare)
```python
from engines.common.identity import RequestContext

ctx = RequestContext(
    tenant_id="t_acme",
    mode="enterprise",
    project_id="proj_xyz"
)
# Raises ValueError if invalid
```

---

## Header Contract (All Transports)

**Required:**
- `X-Mode`: saas | enterprise | lab (REQUIRED)
- `X-Tenant-Id`: ^t_[a-z0-9_-]+$ (REQUIRED)
- `X-Project-Id`: string (REQUIRED)

**Optional:**
- `X-Request-Id`: UUID or string (auto-generated if missing)
- `X-Surface-Id`: string (identity_repo default if missing)
- `X-App-Id`: string (identity_repo default if missing)
- `X-User-Id`: string (from JWT if present)
- `X-Membership-Role`: string (from JWT if present)

**FORBIDDEN:**
- `X-Env`: Any value → 400 Bad Request

---

## Migration Checklist

### ✅ HTTP Routes
- [ ] Import `RequestContext` and `get_request_context` from `engines.common.identity`
- [ ] Add parameter: `ctx: RequestContext = Depends(get_request_context)`
- [ ] Replace manual header extraction with `ctx.tenant_id`, `ctx.mode`, `ctx.project_id`

### ✅ SSE Transport
- [ ] Import `RequestContextBuilder` from `engines.common.identity`
- [ ] Call `RequestContextBuilder.from_request(request)` in handler
- [ ] Catch `ValueError` and return 400 with error detail
- [ ] Use `ctx.mode`, `ctx.tenant_id`, `ctx.project_id` for routing/logging

### ✅ WS Transport
- [ ] Same as SSE transport above
- [ ] Ensure connection handshake validates mode/tenant/project

### ✅ Tests
- [ ] Import `RequestContextBuilder` from `engines.common.identity`
- [ ] Use `RequestContextBuilder.from_headers(headers_dict)` in test setup
- [ ] Assert mode is one of (saas, enterprise, lab)

---

## Troubleshooting

### "X-Mode header is required"
**Issue**: Client not sending X-Mode header  
**Fix**: Ensure client sends one of: `saas`, `enterprise`, `lab`

### "X-Mode must be one of..."
**Issue**: Invalid mode value (e.g., `dev`, `staging`, `prod`)  
**Fix**: Update mode to one of: `saas`, `enterprise`, `lab` (no legacy env values)

### "X-Env header is not allowed"
**Issue**: Client still sending X-Env header  
**Fix**: Remove X-Env from client; use X-Mode instead

### "tenant_id must match pattern"
**Issue**: tenant_id doesn't start with `t_`  
**Fix**: Ensure tenant_id matches ^t_[a-z0-9_-]+$ (e.g., t_acme, t_customer_1)

### "X-Tenant-Id header is required"
**Issue**: Missing X-Tenant-Id header  
**Fix**: Client must send X-Tenant-Id header with valid tenant ID

### "X-Project-Id header is required"
**Issue**: Missing X-Project-Id header  
**Fix**: Client must send X-Project-Id header

---

## Running ModeCTX Tests

```bash
# Run all ModeCTX tests
pytest tests/context/test_mode_headers.py -v

# Run specific test class
pytest tests/context/test_mode_headers.py::TestRequestContextBuilderFromHeaders -v

# Run specific test
pytest tests/context/test_mode_headers.py::TestRequestContextBuilderFromHeaders::test_reject_x_env_header -v
```

---

## Architecture Notes

- **Single Source of Truth**: `engines/common/identity.py` — no parallel identity modules
- **Backward Compat**: JWT decode via `default_jwt_service()`, repo defaults via `identity_repo`
- **No Env Semantics**: Mode replaces legacy env/staging/prod logic
- **Fail-Fast**: Invalid requests rejected at RequestContext boundary with 400
- **Scope Guarantee**: tenant_id + mode + project_id always set on valid RequestContext
