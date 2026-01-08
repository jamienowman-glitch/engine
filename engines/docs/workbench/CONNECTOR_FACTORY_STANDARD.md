# Connector Factory Standard

**Goal**: Enable 1-click addition of new connectors by dropping files into `engines/connectors/`.

## Structure
To add a connector named `my_connector`, create:
```
engines/connectors/my_connector/
  spec.yaml    # Tool definition, scopes, policy requirements
  impl.py      # Python implementation of handlers
```

## `spec.yaml` Contract
```yaml
id: "my_connector"
name: "My Connector"
summary: "Integrates with My Service"
scopes:
  - name: "fetch_data"
    description: "Fetches data from remote"
    handler: "handle_fetch"  # Function name in impl.py
    input_schema:            # JSON Schema for args (or reference Pydantic in impl if loader supports it)
       type: object
       properties:
         id: {type: string}
  - name: "push_data"
    description: "Pushes data"
    handler: "handle_push"
    firearms_required: true  # Optional policy requirement
```

## `impl.py` Contract
Must expose async handler functions matching `spec.yaml` handlers.
Signature: `async def handler(ctx: RequestContext, args: BaseModel | dict) -> Any`

```python
from engines.common.identity import RequestContext
from pydantic import BaseModel

class FetchInput(BaseModel):
    id: str

async def handle_fetch(ctx: RequestContext, args: FetchInput):
    # logic here
    return {"data": "..."}
```
