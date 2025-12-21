# PHASE 7 — Research Runs Log View

> [!NOTE]
> **DONE**: Implemented `ResearchRunService` backed by aggregation of `DatasetEvent` logs. Introduced `InMemoryNexusBackend` to support queryable logs in the absence of a persistent DB connection. `GET /nexus/runs` successfully lists derived runs.

Goal:
- Provide tenant-scoped visibility into Nexus activity (raw ingests, atoms, cards, searches) for operators/Bossman.

In-scope (engines only):
- ResearchRun record: id, tenant_id, env, created_at, created_by/system, kind (ingest/index/search), counts, status, source refs (asset_ids, atom_ids, card_ids), trace_id/request_id.
- Route: `GET /nexus/runs?window_days=...` returning recent runs with pagination; optional filters by kind/status.
- Bossman dashboard extension: expose recent Nexus writes/searches/indexing status using existing logging data.
- DatasetEvents leveraged as source of truth; no new behavior.

Out-of-scope:
- Orchestration over runs; no scheduling; no connector implementations.
- Any interpretation of content beyond counts/ids/timestamps.

Affected engine modules:
- `engines/nexus/logging`, `engines/bossman`, `engines/identity/auth`, `engines/dataset/events`.

Runtime guarantees added:
- Runs list is tenant/env scoped; includes traceability fields; cross-tenant requests blocked.
- Missing window/filter defaults to safe limits; rate limits applied if needed (see Phase 9).

What coding agents will implement later:
- Build run record model/read path backed by DatasetEvents; add tenant-isolation tests; add Bossman read-model.
- Add pagination/window validation; add error handling for missing context.

How we know it’s production-ready:
- Tests show two tenants get disjoint run views; windowing/pagination honored.
- Bossman displays recent Nexus activity with correct counts/status and no cross-tenant leakage.
