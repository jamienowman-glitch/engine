# Collaborative Canvas Contract (CCC v1)

**Status:** DRAFT
**Target:** Northstar Engines V2

## 1. Overview
This contract defines the standard for "Collaborative Canvas" in Northstar. Users (Humans) and Agents interact on a shared, persisted, event-sourced surface. All mutations must pass through a strict command pipeline that guarantees:
- **Identity:** All actions are attributable to a specific Actor (Human/Agent) and RequestContext.
- **Causality:** All mutations are applied on a specific base revision (`base_rev`).
- **Policy:** All mutations are vetted by the GateChain policy engine.
- **Durability:** All accepted mutations are persisted as events and state.

## 2. Core Models

### 2.1 The Document (Scene)
The canonical state of a canvas is the `SceneV2` object.
- **Reference:** [`SceneV2`](file:///Users/jaynowman/dev/northstar-engines/engines/scene_engine/core/scene_v2.py)
- **Serialization:** JSON-compatible Dict (Pydantic).
- **Versioning:** Monotonically increasing integer `revision`.

### 2.2 The Command (Mutation)
State changes are proposed via `CommandEnvelope`.
- **Reference:** [`CommandEnvelope`](file:///Users/jaynowman/dev/northstar-engines/engines/canvas_commands/models.py)
- **Required Fields:**
    - `type` (e.g., `create_node`, `update_transform`)
    - `base_rev` (Optimistic locking token)
    - `idempotency_key` (Replay protection)
    - `args` (Payload)

### 2.3 The Event (Timeline)
Accepted commands become generic events on the timeline.
- **Reference:** [`StreamEvent`](file:///Users/jaynowman/dev/northstar-engines/engines/realtime/contracts.py)
- **Type:** `canvas_commit`
- **Payload:** Contains `cmd_id`, `rev`, `args`.

## 3. The Lifecycle

### 3.1 Loading State (Join)
**Actor** requests `GET /canvas/{id}`.
**Server** determines if it can serve a Snapshot or must Replay.
1.  **Fast Path:** Fetch latest Snapshot `S_last` (Rev satisfying `S.rev > Head - Threshold`).
2.  **Catchup:** Fetch events `E` where `e.rev > S_last.rev`.
3.  **Compute:** `CurrentState = Reduce(S_last, E)`.
4.  **Return:** `CurrentState` + `HeadRev`.

> [!WARNING] (MISSING)
> The `Reduce` function is unimplemented. `engines/canvas_stream/replay.py` is a stub.

### 3.2 Mutating State (Propose)
**Actor** sends `POST /canvas/{id}/command`.
**Server** (Command Service):
1.  **AuthZ:** Validates `RequestContext` & `GateChain` policy. *(Implemented)*
2.  **Lock:** Checks `command.base_rev == current_head_rev`. *(Implemented)*
3.  **Apply:** If match, `NewState = Apply(CurrentState, Command)`. *(MISSING logic)*
4.  **Persist:** Saves Command to `CanvasCommandStore` & Updates Head. *(Implemented)*
5.  **Publish:** Emits `StreamEvent` to Bus/Timeline. *(Implemented)*

### 3.3 Conflict Handling (Reject)
If `command.base_rev != current_head_rev`:
- **Server:** Returns `409 Conflict` (or `200` with `status=conflict`).
- **Payload:** Includes `current_rev` and list of `recovery_ops` (commands that happened since base_rev).
- **Client:** Must Rebase (Operational Transform or Last-Write-Wins strategy) and retry.

## 4. Agent API Surface
Agents are first-class citizens. They use the same API as the Frontend but may prefer a synchronous "Thought -> Action" loop.

| Capability | Method | Endpoint |
| :--- | :--- | :--- |
| **Inspect** | HTTP GET | `/canvas/{id}/snapshot` |
| **Act** | HTTP POST | `/canvas/{id}/command` |
| **Watch** | SSE/HTTP | `/sse/canvas/{id}` or `/canvas/{id}/events?after={seq}` |

## 5. Implementation Status

| Component | Status | Path |
| :--- | :--- | :--- |
| **Command Model** | ✅ DONE | `engines/canvas_commands/models.py` |
| **Command Store** | ✅ DONE | `engines/canvas_commands/store_service.py` |
| **Stream Router** | ✅ DONE | `engines/canvas_stream/router.py` |
| **Event Spine** | ✅ DONE | `engines/event_spine` |
| **Access Control** | ✅ DONE | `engines/realtime/isolation.py`, `GateChain` |
| **Replay Reducer** | ❌ MISSING | `engines/canvas_stream/replay.py` (Stub) |
| **Command Handlers** | ❌ MISSING | (Logic to apply specific commands to SceneV2) |
| **Snapshot Trigger** | ❌ MISSING | (Background task or write-through logic) |
