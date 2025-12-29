# PHASE 7 IMPLEMENTATION PLAN

## Summary
Implement "Research Runs Log View". This phase exposes a read-only view of Nexus activity (ingests, indexing, searches, packs) as "Research Runs". Since Nexus is event-driven, a "Run" is conceptually derived from `DatasetEvent` logs. For this phase, we will implement a service that queries the event log (in-memory for now, or via `InMemoryEventLogger` if accessible, or we aggregate on the fly) to produce `ResearchRun` records.

**Assumption**: Since `default_event_logger` currently just prints or stores in memory (depending on implementation), we need a way to *query* it. I will assume for Phase 7 we introduce a simple `EventLogRepository` or extend `default_event_logger` to support queries, or (simplest) implement an `InMemoryEventLogRepository` that the logger writes to, which the `ResearchRunService` reads from.

## User Review Required
> [!NOTE]
> **Event-Sourced View**: "Runs" are not a separate database table. They are a projection of `DatasetEvent`s.
> **In-Memory Limitation**: Without a persistent DB (Firestore/Postgres) configured in Phase 7, history will be ephemeral (process lifetime). This is acceptable for the "engines" layer contract.

## Proposed Changes

### `engines/logging` (Infrastructure update)
#### [MODIFY] `engines/logging/event_log.py` or similar
- Need to expose a `query_events(tenant_id, ...)` method.
- Currently `default_event_logger` might differ. I will verify if I need to introduce a queryable Store.
- *Decision*: I will create `engines/dataset/events/repository.py` to hold events in-memory, and wire `default_event_logger` to write to it.

### `engines/nexus`
#### [NEW] `engines/nexus/runs`
- **[NEW] [models.py](file:///Users/jaynowman/dev/northstar-engines/engines/nexus/runs/models.py)**:
  - `ResearchRun`: id (trace_id?), tenant_id, env, kind, status, timestamp, counts (cards, atoms).

- **[NEW] [service.py](file:///Users/jaynowman/dev/northstar-engines/engines/nexus/runs/service.py)**:
  - `ResearchRunService`:
    - `list_runs(ctx, window_days)`: Queries event repository for events matching tenant/env. Groups them by `trace_id` (or `interaction_id`) to form a "Run".
    - Example: A `pack_created` event implies a run. Validating `raw_asset_created` implies a run.

- **[NEW] [routes.py](file:///Users/jaynowman/dev/northstar-engines/engines/nexus/runs/routes.py)**:
  - `GET /nexus/runs`: Returns list of `ResearchRun`.

### `engines/chat`
#### [MODIFY] [server.py](file:///Users/jaynowman/dev/northstar-engines/engines/chat/service/server.py):
- Mount `engines.nexus.runs.routes.router`.

## Verification Plan

### Automated Tests
Create `engines/nexus/runs/tests/test_runs.py`:
- **Unit/Integration**:
  - Emit some events (using `default_event_logger`).
  - Call `ResearchRunService.list_runs()`.
  - Verify events are aggregated into Runs correctly.
  - Verify tenant isolation (events from T2 don't show up in T1).

**Command**:
```bash
python -m pytest engines/nexus/runs/tests/test_runs.py
```

### Manual Verification
1. Run server.
2. Trigger some activity (upload file, create card, search).
3. Call `GET /nexus/runs`.
4. Verify recent activity appears.
