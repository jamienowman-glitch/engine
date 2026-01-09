# Canvas Agent API Surface

This document defines the exposed surface for Agents to interact with the Collaborative Canvas.
Agents are treated as first-class Actors with full identity attribution.

## 1. Authentication & Context
Agents must communicate with a valid `RequestContext` identifying them as `ActorType.AGENT`.
- **Identity:** `agent-{uuid}`
- **Auth:** Standard Bearer Token or Internal Ticket.

## 2. Reading State (Sense)
Agents need to "see" the canvas.

### `GET /canvas_commands/snapshot/{canvas_id}`
Returns the latest state of the canvas.
**Response:** `CanvasSnapshot`
```json
{
  "canvas_id": "c_123",
  "head_rev": 42,
  "head_event_id": "evt_abc...",
  "state": {
    "nodes": [ ... ],
    "edges": [ ... ]
  }
}
```
> [!NOTE]
> Currently, the `state` field is empty because the Reducer is unimplemented (See Gap CCC-001).

## 3. Mutating State (Act)
Agents propose changes. They do *not* write to the DB directly.

### `POST /canvas_commands/{canvas_id}/command`
**Body:** `CommandEnvelope`
```json
{
  "id": "cmd_agent_123_xyz",
  "type": "create_node",
  "base_rev": 42,
  "idempotency_key": "idem_123",
  "args": {
    "name": "New Idea",
    "transform": { "x": 100, "y": 100 }
  }
}
```

**Response:** `RevisionResult`
- **Success (200):** `{"status": "applied", "current_rev": 43}`
- **Conflict (409):** `{"status": "conflict", "current_rev": 45, "recovery_ops": [...]}`
    - **Behavior:** The Agent must *Read State* again (fetch rev 45) and re-plan its action.

## 4. Listening (Observe)
Agents can listen for real-time updates to react to other agents or humans.

### `GET /sse/canvas/{canvas_id}`
**Headers:** `Last-Event-ID: {previous_event_id}`
**Stream:**
```
event: canvas_commit
data: { "cmd_id": "...", "type": "create_node", "rev": 43, "args": {...} }

event: gesture
data: { "actor_id": "user_bob", "cursor": { "x": 120, "y": 100 } }
```

## 5. Python Client (Proposed)
A simplification wrapper for Agents.

```python
class CanvasAgentClient:
    def get_state(self, canvas_id: str) -> SceneV2:
        # Fetches snapshot
        pass
        
    def apply(self, canvas_id: str, action: str, args: dict, base_rev: int) -> int:
        # Sends command, handles 409 retry loop (optional)
        pass
        
    def stream(self, canvas_id: str):
        # Yields events
        pass
```
