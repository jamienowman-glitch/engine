# Phase 0.5 — Infra Routing TODO (AWS/GCP/Azure switchable, generic surfaces)

## Executive Summary
- Current state: env/in-memory selection across domains (vector/Haze, object store, memory, KPI/metrics, timeline); routing registry exists but is unused by these services.
- Phase 0.5 aim: routing registry is the only selector; sellable modes (t_system/enterprise/saas) must resolve to cloud-class backends; filesystem allowed only in lab; auditable/manual switches only.
- Invariants: no monolith configs, no orchestrator router, GateChain unchanged, no env-driven backend selection, no in-memory defaults in real runs, surfaces generic (SQUARED² only an alias test).

## Lane Plan (checkboxes)
- [ ] Lane 0 — Scope + normalization helper
  - Add canonical surface normalization used in routing resolution only (aliases incl. SQUARED² -> squared2 internal).
  - DoD: routes accept alias, registry stores canonical; tests for alias round-trip.

- [ ] Lane 1 — Routing registry real
  - Resource_kind constants (vector_store, object_store, tabular_store, event_stream, metrics_store, memory_store, kpi_store optional).
  - Persisted registry (filesystem default), control-plane API (upsert/get/list), audit + StreamEvent on changes, strategy lock/role guard.
  - DoD: registry survives restart; change emits audit + stream; curl upsert/list works.

- [ ] Lane 2 — Filesystem adapters (lab-only poor-man)
  - Implement/standardize filesystem adapters for: event_stream append-log; object_store blobs; tabular_store JSONL/SQLite; metrics_store JSONL (raw metrics); memory_store (session/blackboard/maybes); vector_store filesystem/FAISS stub.
  - Enforce lab-only: routing resolution guard rejects filesystem/in-memory when ctx.mode ∈ {t_system, enterprise, saas}.
  - DoD: lab routes operate via filesystem with evidence files; sellable modes hard-fail on local backends.

- [ ] Lane 3 — Wire domains to routing registry (remove env gates)
  - Domains: timeline/event_stream (replace STREAM_TIMELINE_BACKEND), object store/media/raw_storage, tabular/policy store, metrics/raw metrics store, memory/maybes selection, vector store selection.
  - Backend-class guard: sellable modes must resolve to cloud backend_class; fail fast if route points to filesystem/in_memory.
  - DoD: env vars no longer select backend; routes drive selection; lab works with filesystem, sellable modes reject local; at least one cloud backend path works (Firestore/GCS/S3 as available).

- [ ] Lane 4 — Cloud adapters (real first, stubs allowed)
  - Object_store: keep GCS; add S3 adapter; allow Azure Blob placeholder (NotImplemented).
  - Event_stream/tabular/metrics: allow Firestore/Dynamo/Cosmos placeholders (fail-fast) if not implemented.
  - DoD: selecting S3 route performs PUT/GET (with creds); selecting missing adapter returns explicit NotImplemented (no silent fallback).

- [ ] Lane 5 — t_system surfacing (diagnostics + manual switching)
  - Read-only view of routing per resource_kind; manual switch route guarded by strategy lock/role; diagnostic metadata (free tier/quota notes, cost risk, health timestamps), no secrets.
  - DoD: switching emits audit + StreamEvent; view shows current routes.

## Do-not-break invariants
- No env-driven backend selection; no in-memory defaults for real runs; no monolith config files; no “one function to route everything”; GateChain logic unchanged (only dependencies routed).

## Commit slicing (ordered)
1) normalization helper (Lane 0)
2) registry resource_kinds + persistence + API + audit/stream events (Lane 1)
3) filesystem adapters (lab-only) for all domains + backend-class guard (Lane 2)
4) wire domains to registry, remove env gates (Lane 3)
5) cloud adapter: S3 object_store + placeholders/fail-fast for others (Lane 4)
6) t_system surfacing hooks (Lane 5; if UI elsewhere, track separately)
