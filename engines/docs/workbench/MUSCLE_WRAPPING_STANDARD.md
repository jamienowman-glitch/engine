# Muscle Wrapping Standard

**Goal**: Expose internal engines as MCP tools via standard wrappers.

## 1. Location
Wrappers live in `engines/muscles/<muscle_name>/mcp/impl.py` (or `mcp_wrapper.py` if preferred by local convention, but `mcp/impl.py` is the current standard).
`spec.yaml` must accompany the implementation.

## 2. Wrapping Pattern
The wrapper should be a thin layer converting `RequestContext` and Pydantic models into calls to the underlying Service.

```python
# engines/muscles/media/mcp/impl.py
from engines.muscle.media_v2.service import get_media_service
from engines.common.identity import RequestContext
from pydantic import BaseModel

class ListAssetsInput(BaseModel):
    limit: int = 10

async def handle_list_assets(ctx: RequestContext, args: ListAssetsInput):
    svc = get_media_service()
    return svc.list_assets(ctx, limit=args.limit)
```

## 3. Policy Enforcement
- **Read Operations**: Check `GateChain` if sensitive, otherwise generally open if authenticated.
- **Mutating Operations**: MUST call `GateChain.run(ctx, action=..., ...)` inside the wrapper or service.
- **Defaults**: Default is Open (Firearms Required = False). Overlay applies restrictions.

## 4. Error Handling
- Use `engines.common.error_envelope.ErrorEnvelope` for all errors.
- Do not raise raw exceptions; use `HTTPException` with properly formatted details if possible, or let the standard error handler catch them.
