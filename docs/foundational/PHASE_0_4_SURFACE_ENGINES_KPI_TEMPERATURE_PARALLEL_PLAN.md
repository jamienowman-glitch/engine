# Phase 0.4 — Surface Engines KPI + Temperature Parallel Plan

## Two-worker plan
- Worker A (Normalization + KPI):
  1) Add surface normalizer helper (engines/common/surface_normalizer.py) and apply to KPI routes/service/repo selection.
  2) Implement FileKpiRepository (filesystem default), wire service to use it (no env-driven in prod), add SurfaceKpiSet model + routes.
  3) Add raw KPI ingestion store (filesystem) and GateChain KPI value enforcement.
  4) Seed SQUARED² KPI set/config; update tests for aliasing and persistence.
  Commit order: A1 normalization, A2 KPI persistence, A3 raw ingestion + GateChain value checks, A4 KPI set + seed/tests.

- Worker B (Temperature):
  1) Apply surface normalizer to Temperature routes/service.
  2) Implement FileTemperatureRepository (filesystem default) with separate floors/ceilings/weights/snapshots; wire service defaults (weights independent).
  3) Seed SQUARED² temperature defaults; update tests for aliasing and weight independence.
  Commit order: B1 normalization usage, B2 temperature persistence, B3 seed/tests.

Dependency: Worker B starts after normalization helper merged (A1). Seeds after persistence. GateChain KPI enforcement depends on raw ingestion store.

## Three-worker plan
- Worker A: Normalization helper + integration into KPI and Temperature code paths (shared module, minimal touch).
- Worker B: KPI persistence + surface KPI set + raw ingestion + GateChain KPI value enforcement + KPI tests/seeds.
- Worker C: Temperature persistence (floors/ceilings/weights separate) + seeds + Temperature tests.

Ordering:
1) A merges normalization.
2) B and C branch from normalized main; B and C land in either order (independent, except B’s GateChain change consumes normalization only).
3) Final pass: ensure GateChain KPI/Temperature calls use normalized surfaces; rerun acceptance (including raw ingestion and weight independence checks).

## Commit sequencing (max 4 commits)
1) normalization: add helper + wire KPI/Temperature reads/writes to use it.
2) kpi-persistence: add FileKpiRepository + SurfaceKpiSet + service/routes wiring; filesystem default.
3) temperature-persistence: add FileTemperatureRepository + service wiring; filesystem default (weights separate).
4) kpi-raw+gatechain: add raw ingestion store and GateChain KPI value enforcement.
5) seeds/tests: seed SQUARED² KPI/Temperature defaults; update tests for aliasing, raw persistence, and weight independence proofs.
