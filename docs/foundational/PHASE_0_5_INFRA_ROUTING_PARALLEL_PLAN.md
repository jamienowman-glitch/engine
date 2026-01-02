# Phase 0.5 — Infra Routing Parallel Plan

## Two-worker split
- Worker A: Normalization + registry + filesystem adapters
  1) Add surface normalization helper and integrate into routing resolution.
  2) Enhance routing registry (resource_kinds, filesystem persistence, API, audit/stream).
  3) Implement filesystem adapters for event_stream/object_store/tabular_store/metrics_store/memory_store/vector stub.
  Commit order: A1 normalization, A2 registry, A3 filesystem adapters.

- Worker B: Domain wiring + cloud adapter + t_system surfacing
  1) Wire domains (vector, object_store, event_stream, metrics/KPI, memory/maybes) to registry; remove env gates.
  2) Add S3 object_store adapter (plus explicit placeholders for other clouds).
  3) Add route change audit + strategy lock guard + diagnostics view (t_system hooks tracked if external).
  Commit order: B1 wiring/removal of env, B2 S3 adapter/placeholders, B3 audit/surfacing hooks.

Dependency: B starts after A2 (registry present). Merge A before B to avoid wiring conflicts.

## Three-worker split
- Worker A: Normalization helper + registry (resource_kinds, persistence, API, audit/stream).
- Worker B: Filesystem adapters for all domains.
- Worker C: Domain wiring (remove env), cloud adapter (S3), audit/surfacing hooks.

Ordering:
1) A merges normalization+registry.
2) B adds filesystem adapters (independent once registry exists).
3) C wires domains and adds S3/audit/surfacing; final reconciliation of small touchpoints in services.

## Merge rules
- Prefer sequential merges per commit slicing: normalization → registry → filesystem adapters → wiring → cloud → surfacing.
- Coordinate touches in service factory functions to avoid conflicts (domain wiring likely edits service/repo selection helpers).
- Tests/docs updated in each lane to avoid cross-branch drift.***
