# Muscle MCP Implementation Plan

**Objective:** Wrap all identified muscles (`engines/muscle/*`) into standardized MCP wrappers (`engines/muscles/*`) to be exposed via the Workbench.

## 1. The Repeatable Loop

For each task in `MUSCLE_MCP_BACKLOG.tsv`:

1.  **Select Task Batch:** Pick `N` related tasks (e.g., all `video_*` read scopes, or all `audio_*` scopes).
2.  **Verify Service:** Check `engines.muscle.<muscle_id>.service` for the method required. If missing, mark as blocked or wire to `NotImplemented`.
3.  **Scaffold Wrapper:**
    *   Create/Ensure `engines/muscles/<muscle_id>/mcp/spec.yaml`.
    *   Create/Ensure `engines/muscles/<muscle_id>/mcp/impl.py`.
4.  **Implement Handler:**
    *   Import service factory (e.g., `get_service()`).
    *   Define Input Model (Pydantic).
    *   Implement async handler function.
    *   **CRITICAL:** Add `GateChain` enforcement if `needs_gatechain=true`.
    *   **CRITICAL:** Add `GateChain` overlay lookup using `(tool_id, scope_name)`.
5.  **Register:**
    *   Add scope definition to `spec.yaml`.
    *   Ensure `impl.py` exports the handler and input model.
6.  **Test:**
    *   Create `engines/mcp_gateway/tests/test_wrapper_<muscle_id>.py` (or shared test file).
    *   Test: Discovery (loader finds it).
    *   Test: Execution (happy path calling mock service).
    *   Test: Policy (mock GateChain rejection).
7.  **Enable:**
    *   Add `muscle_id` to `ENABLED_MUSCLES` environment variable in local dev/CI.

## 2. The "One True Wrapper Shape"

Every wrapper MUST follow this structure.

### File Structure
```
engines/muscles/<muscle_id>/
├── mcp/
│   ├── spec.yaml
│   └── impl.py
```

### spec.yaml
```yaml
id: <muscle_id>
name: <Human Readable Name>
summary: <Description>
scopes:
  - name: <namespace>.<operation>  # e.g. video.timeline.read
    description: <Description>
    handler: <function_name>       # e.g. handle_read
    input_model: <class_name>      # e.g. ReadInput
    firearms_required: false       # ALWAYS false in static spec; policy handles checks.
```

### impl.py
```python
from typing import Any, Optional
from pydantic import BaseModel, Field
from engines.common.identity import RequestContext
from engines.nexus.hardening.gate_chain import GateChain
from engines.muscle.<muscle_id>.service import get_service

# 1. Input Models
class ReadInput(BaseModel):
    operation: str  # sub-dispatch if scope gathers multiple reads
    arg1: str
    ...

# 2. Handler
async def handle_read(ctx: RequestContext, args: ReadInput) -> Any:
    # 3. Policy Enforcement (Runtime)
    # Action = Scope Name
    GateChain().run(
        ctx, 
        action="<scope_name>", 
        subject_id=args.id,
        subject_type="<resource_type>", # e.g. video_project
        surface="<muscle_id>"
    )

    # 4. Service Delegation
    svc = get_service()
    return svc.some_method(args.arg1)
```

## 3. Agent Touch Boundaries

*   **ALLOWED:** Creating/Editing files in `engines/muscles/**`.
*   **ALLOWED:** Reading/Importing from `engines/muscle/**`.
*   **FORBIDDEN:** Modifying `engines/muscle/**` (Service Logic).
*   **FORBIDDEN:** Modifying `engines/mcp_gateway/*.py` (Core Gateway Logic).
*   **FORBIDDEN:** Modifying `engines/workbench/dynamic_loader.py`.

## 4. Error Handling Standard

Wrappers must let Service exceptions bubble up, OR wrap them in standard standard errors if the service is untyped.
Gateway middleware handles the final 500/400 mapping.
Wrappers should validate INPUTs using Pydantic.

## 5. GateChain & Firearms

*   **NEVER** hardcode `firearms_required=True` in `spec.yaml`.
*   **NEVER** hardcode license checks in `impl.py`.
*   **ALWAYS** call `GateChain().run(...)`.
*   GateChain will check the Policy Store (Activation Overlays) to see if "Firearms" or "License" is required for this user/scope tuple.
