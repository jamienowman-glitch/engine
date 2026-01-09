# Canvas Core Reality Map

**Last Updated:** 2026-01-09
**Scope:** `engines` repo (Canvas V2 / Collaborative Contract)

## 1. Where State Lives
The "Canvas" concept is currently split between a persistent command log (Source of Truth) and a computed snapshot (Derived View).

| Concept | Location | Implementation Class | Status |
| :--- | :--- | :--- | :--- |
| **Command Log** | `engines/canvas_commands/store_service.py` | `CanvasCommandStoreService` | **EXISTING** (TabularStore) |
| **Snapshots** | `engines/canvas_commands/models.py` | `CanvasSnapshot` (Model only) | **MISSING** (Service logic incomplete) |
| **Head Revision** | `engines/canvas_commands/store_service.py` | `CanvasCommandStoreService.get_head_revision` | **EXISTING** |
| **Scene Graph** | `engines/scene_engine/core/scene_v2.py` | `SceneV2` | **EXISTING** (Pydantic Model) |
| **Scene Persistence** | `engines/scene_engine/store/service.py` | `SceneStoreService` | **EXISTING** (Firestore/blob) |

> [!NOTE]
> `SceneStoreService` currently saves full blobs of `SceneV2`. This is disconnected from `CanvasCommandStoreService` which saves atomic commands. The convergence point (Snapshot = Reduce(Logs)) is defined in `engines/canvas_stream/replay.py` but is currently a stub.

## 2. Where Events Live
Events move through a transport layer (ephemeral/hot) and settle into a durable timeline (cold/warm).

| Concept | Location | Implementation Class | Status |
| :--- | :--- | :--- | :--- |
| **Event Envelope** | `engines/realtime/contracts.py` | `StreamEvent` | **EXISTING** |
| **Durable Spine** | `engines/event_spine/cloud_event_spine_store.py` | `FirestoreEventSpineStore`, `DynamoDBEventSpineStore` | **EXISTING** |
| **Timeline View** | `engines/realtime/timeline.py` | `FirestoreTimelineStore` | **EXISTING** |
| **Transport Bus** | `engines/chat/service/transport_layer.py` | `InMemoryBus`, `LazyBus` | **LEGACY / HYBRID** |
| **Stream API** | `engines/canvas_stream/router.py` | `stream_canvas` (SSE endpoint) | **EXISTING** |
| **Command Envelope** | `engines/canvas_commands/models.py` | `CommandEnvelope` | **EXISTING** |

> [!IMPORTANT]
> The "Bus" is currently `InMemoryBus` (observational only) or `RedisBus`. It is **NOT** durable. Durability is achieved by writing to `TimelineStore` (or `EventSpine`) *in parallel* with bus publication. This dual-write pattern is evident in `engines/chat/service/transport_layer.py`.

## 3. How Replay Works
Replay is the mechanism of reconstructing state or client view from the event log.

| Component | Reality | Findings |
| :--- | :--- | :--- |
| **Stream Replay** | `engines/canvas_stream/router.py` | Client sends `Last-Event-ID`. Server fetches `timeline_store.list_after()`. Works for *events*, not necessarily *state*. |
| **State Reconstruction** | `engines/canvas_stream/replay.py` | `ReplayService.generate_keyframe` is a **STUB**. It returns an empty node list. |
| **Command Replay** | `engines/canvas_commands/service.py` | `get_canvas_replay` fetches raw commands from `CanvasCommandStoreService`. |

**CRITICAL GAP:** There is no "Reducer" that takes `List[CommandEnvelope]` and produces `SceneV2`.

## 4. Identity & Actor Model
Identity is robust, strictly typed, and ubiquitous.

| Component | Location | Details |
| :--- | :--- | :--- |
| **RequestContext** | `engines/common/identity.py` | Passed everywhere. Contains `tenant_id`, `user_id`, `mode`, `surface_id`. |
| **Actor Types** | `engines/realtime/contracts.py` | `ActorType.HUMAN`, `ActorType.AGENT`, `ActorType.SYSTEM`. |
| **Auth Context** | `engines/identity/auth.py` | Validated via JWT or Ticket. Enforces strict multitenancy. |
| **Policy Hook** | `engines/nexus/hardening/gate_chain.py` | `GateChain` checks permissions (RBAC/ABAC) on every command/gesture. |

## 5. Agent Interaction Paths
How an automated agent would interact with the canvas today.

- **Read State:** `GET /canvas/commands/{canvas_id}/snapshot` (via `get_canvas_snapshot` in `service.py`) -> **Likely broken/empty** due to missing reducer.
- **Mutate:** Call `apply_command(command_envelope)`.
    - Requires: `CommandEnvelope` with valid `base_rev`.
    - Outcome: Emits `canvas_commit` event to SSE.
- **Listen:** Connect to SSE `/sse/canvas/{canvas_id}`.
    - receives `StreamEvent` with `type=canvas_commit` or `gesture`.

## 6. Missing Pieces (The Gap)

1.  **The Reducer:** No code exists to apply a `create_node` command to a `SceneV2` object.
2.  **Snapshotting Strategy:** No trigger to periodic snapshot `SceneV2` to `SceneStoreService`.
3.  **Agent "Tool" Definition:** No formalized MCP tool or Agent Contract for "Canvas Mutator".
4.  **Deterministic Replay Test:** No test proving `State(T0) + Events(T0..T1) == State(T1)`.
