# Phase 0.5 — Infra Routing TODO (AWS/GCP/Azure switchable, generic surfaces)

## Executive Summary
- Current state: many domains select backends via env or default to in-memory (vector/Haze, object store, memory, KPI/metrics, timeline); routing registry exists but unused.
- Phase 0.5 aim: make routing a control-plane primitive per resource_kind + RequestContext (tenant/mode/project/app/surface), filesystem as baseline poor-man backend, auditable/manual switches only.
- Invariants: no monolith configs, no orchestrator router, GateChain unchanged, no env-driven backend selection, no in-memory defaults in real runs, surfaces generic (SQUARED² only an alias test).

## Lane Plan (checkboxes)
- [ ] Lane 0 — Scope + normalization helper
  - Add canonical surface normalization used in routing resolution only (aliases incl. SQUARED² -> squared2 internal).
  - DoD: routes accept alias, registry stores canonical; tests for alias round-trip.

- [ ] Lane 1 — Routing registry real
  - Resource_kind constants (vector_store, object_store, tabular_store, event_stream, metrics_store, memory_store, kpi_store optional).
  - Persisted registry (filesystem default), control-plane API (upsert/get/list), audit + StreamEvent on changes, strategy lock/role guard.
  - DoD: registry survives restart; change emits audit + stream; curl upsert/list works.

- [ ] Lane 2 — Filesystem adapters (poor-man for every domain)
  - event_stream filesystem append-log; object_store filesystem blob; tabular_store filesystem JSONL/SQLite; metrics_store filesystem JSONL (raw KPI inputs); memory_store filesystem for session/blackboard/maybes; vector_store filesystem/FAISS stub.
  - DoD: fresh clone/no cloud creds — all domains operate via filesystem routes; evidence files created.

- [ ] Lane 3 — Wire domains to routing registry (remove env gates)
  - Vector selection via registry (Vertex target still available); timeline via registry; memory/maybes via registry; object store/media via registry; KPI/metrics via registry.
  - DoD: env vars no longer select backend; deleting env still works via filesystem routes.

- [ ] Lane 4 — Cloud adapters (real first, stubs allowed)
  - S3 object_store adapter; keep GCS; placeholders for AWS/Azure vector/tabular with explicit NotImplemented.
  - DoD: selecting S3 route performs PUT/GET; selecting placeholder returns explicit NotImplemented (no silent fallback).

- [ ] Lane 5 — t_system surfacing (diagnostics + manual switching)
  - Read-only view of routing per resource_kind; manual switch route guarded by strategy lock/role; diagnostic metadata (free tier/quota notes, cost risk, health timestamps), no secrets.
  - DoD: switching emits audit + StreamEvent; view shows current routes.

## Do-not-break invariants
- No env-driven backend selection; no in-memory defaults for real runs; no monolith config files; no “one function to route everything”; GateChain logic unchanged (only dependencies routed).

## Commit slicing (ordered)
1) normalization helper (Lane 0)
2) registry resource_kinds + persistence + API + audit/stream events (Lane 1)
3) filesystem adapters for all domains (Lane 2)
4) wire domains to registry, remove env gates (Lane 3)
5) cloud adapter: S3 object_store + placeholders for others (Lane 4)
6) t_system surfacing hooks (Lane 5; if UI elsewhere, track separately)
