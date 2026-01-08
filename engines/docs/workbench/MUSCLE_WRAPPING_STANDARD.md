# Muscle Wrapping Standard

**Authority**: Northstar Engines  
**Goal**: Expose internal "muscles" (Engine Capabilities) as MCP Tools.

## 1. Location

Muscle wrappers live alongside the muscle implementation OR in `engines/connectors/internal/<muscle_id>/`.
*Preferred*: `engines/muscles/<muscle_id>/mcp_wrapper.py` (Colocation).

## 2. Wrapper Responsibilities

A Muscle Wrapper is an adapter that converts:
1.  **MCP Input** (JSON/Pydantic) -> **Muscle Native Input** (Typed Objects)
2.  **Context**: Propagates `RequestContext` (Trace ID, User ID).
3.  **Output**: Native Result -> MCP Result (JSON).

## 3. Required Patterns

### Identity Propagation
Muscles require `RequestContext`. You must pass the context from the MCP handler to the muscle.

```python
# GOOD
async def handler(ctx: RequestContext, input: MyInput):
    return await my_muscle.execute(ctx, input.param)
```

### Error Envelopes
Do not leak stack traces. Catch muscle exceptions and wrap in `ErrorEnvelope` or use standard `error_response`.

```python
try:
    result = muscle.do_thing()
except MuscleError as e:
    # Map to standardized MCP error
    return error_response("muscle.failure", str(e))
```

### GateChain Checks
Muscles typically perform their own GateChain checks (Firearms).
The Wrapper should NOT double-enforce unless the muscle is "raw" and unsafe.
*Rule of Thumb*: If the muscle function raises `FirearmsException`, let it bubble to the Gateway's error handler (which maps to 403).

## 4. Multi-Scope Design
One Muscle != One Scope.
Break muscles down:
- `video:render` (Write/Heavy)
- `video:status` (Read/Light)
- `video:list_presets` (Read/Static)

Register these as separate scopes in the Inventory.
