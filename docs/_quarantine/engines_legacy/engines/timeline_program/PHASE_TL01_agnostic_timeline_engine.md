# PHASE_TL01_agnostic_timeline_engine

## 1. Goal  
Provide a domain-agnostic timeline engine that stores tasks, dependencies, dates, and meta per tenant and emits a JSON shape suitable for a Gantt-like viewer. Domain adapters (CAD plan-of-works, marketing content plans, media timelines) map their objects into this core without forking logic.

## 2. North star + Definition of Done  
- North star:  
  - CAD tenant: CAD ingest → BoQ → plan-of-works → see a Gantt of tasks by level/zone/trade with dates, costs, and dependencies using the same timeline_core.  
  - Marketing tenant: push a content plan (campaigns/assets/channels) → see a content calendar/timeline via the same core.  
  - Video/media: may consume this core later as a client; not required to modify video engines.  
- Definition of Done (TL01):  
  - Core models: `timeline_task` (id, tenant_id, env, title, start_ts, end_ts or duration, status enum, tags, grouping fields, source_kind/source_id, meta JSON, request_id), `timeline_dependency` (from_task_id, to_task_id, type, meta), optional grouping/lane fields for Gantt view.  
  - CRUD + query APIs scoped by tenant/env, with filtering (date range, tags, groupings) and 4xx validation on bad inputs.  
  - Deterministic ID/hash rules for tasks generated from upstream artifacts (e.g., CAD BoQ/plan-of-works) to ensure idempotent regeneration.  
  - View-model JSON for Gantt (rows/lanes, tasks with display fields, dependencies) that can be rendered without extra joins.  
  - Basic per-tenant safety: no cross-tenant leakage; RequestContext and tenant/env required on all writes/reads.  
  - Tests proving determinism, dependency ordering/topological sorting, scope tagging/filtering, and cycle detection/handling.

## 3. Scope (In / Out)  
- In:  
  - Backend models/services/routes for timeline_core (CRUD, list, view-model).  
  - Adapters (within allow-list) describing how to build timeline tasks from CAD plan-of-works/BoQ and generic content plans (implementation within timeline_core).  
- Out:  
  - UI/Gantt visualization code (only JSON contract defined).  
  - New auth/tenant frameworks (use existing RequestContext patterns).  
  - Agent graphs/orchestration, Nexus/connectors, or any /ui, /core, /tunes changes.

## 4. Modules to touch (hard allow-list)  
- engines/timeline_core/models.py  
- engines/timeline_core/service.py  
- engines/timeline_core/routes.py  
- engines/timeline_core/tests/test_models.py  
- engines/timeline_core/tests/test_service.py  
- engines/timeline_core/tests/test_routes.py  
- docs/engines/timeline_program/PHASE_TL01_agnostic_timeline_engine.md  
- docs/engines/timeline_program/TIMELINE_CORE_TODOS.md  
- **READ-ONLY CONTEXT:** engines/boq_quantities/, engines/plan_of_work/ (for adapter inputs), other domain engines (video, marketing) are not to be modified.  
> STOP RULE: If you believe any file outside this list must be changed, STOP and report instead of editing it.

## 5. Implementation checklist (mechanical)  
- **T01.1 – Core models:** Define Task, Dependency, Status enum, tags/grouping fields, source_kind/source_id, request_id; validate tenant/env/start<=end; compute deterministic id/hash when source provided.  
- **T01.2 – Deterministic IDs from upstream:** Hash rules for tasks derived from CAD BoQ/plan-of-works (e.g., tenant|env|source_kind|source_id|grouping fields) to enable idempotent regeneration; store hash in meta.  
- **T01.3 – Service CRUD/query:** Create/update/delete tasks and dependencies; list by tenant/env with filters (date range, tags, groupings, status); enforce no cross-tenant access; topological order helper; cycle detection with clear error.  
- **T01.4 – CAD adapter:** In timeline_core, add adapter to build tasks from plan_of_work/boq_quantities inputs (read-only sources) with grouping fields (level, zone, trade), duration, cost meta; deterministic ids.  
- **T01.5 – Content-plan adapter:** Adapter to build tasks from generic content plan payload (campaign/channel/asset/due_date/owner/tags) with deterministic ids; validation of required fields.  
- **T01.6 – View-model JSON for Gantt:** Assemble per-tenant Gantt JSON (lanes/rows/grouping, tasks with display fields, dependencies, color/status mapping); deterministic ordering.  
- **T01.7 – Validation & constraints:** Enforce tenant/env/request_id required; reject invalid date ranges; dependency types validated; cycle detection; max page size defaults.  
- **T01.8 – HTTP API:** Routes for CRUD/list/build-from-adapter/view-model; stable response schemas; 4xx on validation failures; no auth changes.  
- **T01.9 – Docs/examples:** Add examples for CAD and marketing use cases, showing inputs and resulting Gantt JSON shape; describe how a UI could consume it.

## 6. Tests  
- engines/timeline_core/tests/test_models.py — model validation (tenant/env, start<=end), status enum, hash determinism for source-derived tasks.  
- engines/timeline_core/tests/test_service.py — CRUD, list filters (date range, tags, grouping), deterministic regeneration from adapters, topological ordering, cycle detection behavior, tenant scoping.  
- engines/timeline_core/tests/test_routes.py — HTTP validation (4xx on bad input), CRUD/list/view-model endpoints, tenant/env required.  
- Command examples:  
  - `python3 -m pytest engines/timeline_core/tests/test_models.py`  
  - `python3 -m pytest engines/timeline_core/tests/test_service.py`  
  - `python3 -m pytest engines/timeline_core/tests/test_routes.py`

## 7. Docs & examples  
Please refer to `engines/timeline_core/README.md` for detailed documentation, including:
- CAD and Marketing adapter usage.
- API endpoints and curl examples.
- Gantt view JSON structure.

## 8. Guardrails  
- Do not touch any auth/tenant/RequestContext/strategy lock/firearms/budget/safety code.  
- Do not touch any /ui, /core, or /tunes directories.  
- Do not modify any connectors, orchestration flows, manifests, or Nexus/agent behaviour.  
- Do not add or change any vector store / memory / logging pipelines; use existing patterns only.  
- If external API/model shapes change, mark CONTRACT CHANGE in this doc and limit edits to the allow-listed timeline_core files and matching tests.

## 9. Execution note  
Workers must deliver code + tests + docs strictly within the allow-listed files to meet the Definition of Done. If work seems to require edits outside the allow-list, STOP and report. After TL01 completes, run a fresh architect audit before defining subsequent phases.
