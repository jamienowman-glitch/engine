# PHASE 8 IMPLEMENTATION PLAN

## Summary
Implement "Session Memory Placeholder". The goal is to provide a minimal, tenant-scoped primitive for storing session turns (user input + agent output) without any semantic processing (no RAG/reasoning yet). This acts as the storage layer for conversation history.

**Scope**:
- `SessionTurn`: Data model for a single interaction.
- `SessionMemoryService`: Service to store and retrieve specific turns or entire session history.
- **Tenancy**: Strictly enforced `tenant_id` + `env` + `user_id`.
- **Ops**: Logging of writes via `DatasetEvent`.

## User Review Required
> [!NOTE]
> **Placeholder Nature**: This uses in-memory storage (matching Phase 7 backend pattern) or a simple stub. It does not persist to DB in this phase.
> **No Interpretation**: The engine stores text blobs. It does not summarize or vectorize them (that's future scope).

## Proposed Changes

### `engines/nexus`
#### [NEW] `engines/nexus/memory`
- **[NEW] [models.py](file:///Users/jaynowman/dev/northstar-engines/engines/nexus/memory/models.py)**:
  - `SessionTurn`: session_id, turn_id, role (user/agent), content, timestamp, references.
  - `SessionSnapshot`: session_id, turns list, summary (optional).

- **[NEW] [service.py](file:///Users/jaynowman/dev/northstar-engines/engines/nexus/memory/service.py)**:
  - `SessionMemoryService`:
    - `add_turn(ctx, session_id, turn)`: Appends turn to session storage.
    - `get_session(ctx, session_id)`: Retrieves history.

- **[NEW] [routes.py](file:///Users/jaynowman/dev/northstar-engines/engines/nexus/memory/routes.py)**:
  - `POST /nexus/memory/session/{session_id}/turn`: Append turn.
  - `GET /nexus/memory/session/{session_id}`: Get full session.

### `engines/chat`
#### [MODIFY] [server.py](file:///Users/jaynowman/dev/northstar-engines/engines/chat/service/server.py):
- Mount `engines.nexus.memory.routes.router`.

## Verification Plan

### Automated Tests
Create `engines/nexus/memory/tests/test_memory.py`:
- **Unit/Integration**:
  - Store turns for Session A (Tenant 1).
  - Verify retrieval returns correct order.
  - Verify Tenant 2 cannot access Session A.

**Command**:
```bash
python -m pytest engines/nexus/memory/tests/test_memory.py
```

### Manual Verification
1. Run server.
2. POST a turn to a new session ID.
3. GET the session ID.
4. Verify turn matches.
