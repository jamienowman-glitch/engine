# PHASE_VIEW01_cad_gantt_and_overlays

## 1. North star + Definition of Done  
- North star: For a single tenant/project, the user can run CAD01–05 (ingest → semantics → BoQ → cost → plan-of-works) and then call viewer APIs to get:  
  - Gantt-ready JSON timeline (tasks, start/end dates, dependencies, trades) that can feed TL01 or any Gantt UI.  
  - Plan overlay JSON: per element/room show quantities, units, costs, and placeholder risk flags (read-only).  
  - Both JSON blobs are deterministic (hash/IDs derived from upstream artifacts) and read-only over CAD artifacts.  
- Definition of Done:  
  - View-model schemas defined (fields, required/optional, types): CadGanttView (tasks, dependencies, meta) and CadOverlayView (elements/rooms with quantities, units, costs, trade/level/zone, meta).  
  - Deterministic hashes/IDs based on upstream artifact hashes/versions.  
  - Read-only service that loads cad_model/cad_semantics/boq_quantities/cost_model/plan_of_work artifacts via media_v2 and emits view-models; no writes/mutations.  
  - At least two documented fixtures (small house, small extension) with expected JSON shapes.  
  - HTTP endpoints to serve view-models; clear errors when required artifacts are missing.  
  - Ready to feed TL01 view-model or a generic UI canvas without further joins.

## 2. Scope (In / Out)  
- In:  
  - Read cad_model, cad_semantics, boq_quantities, cost_model, plan_of_work artifacts via media_v2.  
  - Map to CadGanttView and CadOverlayView JSON view-models.  
  - HTTP endpoints to serve these view-models.  
- Out:  
  - No drawing/HTML/SVG/CSS (viewer only outputs JSON).  
  - No auth/tenant framework changes.  
  - No orchestration/agent/diff/risk/portfolio rules (CAD06–08).  
  - No writes back into CAD engines.

## 3. Modules to touch (hard allow-list)  
- engines/cad_viewer/models.py  
- engines/cad_viewer/service.py  
- engines/cad_viewer/routes.py  
- engines/cad_viewer/tests/test_gantt_view.py  
- engines/cad_viewer/tests/test_overlay_view.py  
- engines/media_v2/models.py (only if adding view-model artifact kinds; tag CONTRACT CHANGE)  
- engines/media_v2/tests/test_validation_strict_cad_viewer.py (only if CONTRACT CHANGE)  
- docs/engines/viewer_program/PHASE_VIEW01_cad_gantt_and_overlays.md  
> STOP RULE: If you believe any file outside this list must be changed to complete this phase, stop and return a report instead of editing it.

## 4. Guardrails for implementers  
- Do not touch any auth/tenant/RequestContext/strategy lock/firearms/budget/safety code.  
- Do not touch any /ui, /core, or /tunes directories.  
- Do not modify connectors, orchestration flows, manifests, or Nexus/agent behaviour; this phase is engines-only muscle.  
- Do not add/change any vector store / memory / logging pipelines; only use existing helpers in the allowed modules.  
- If a new artifact kind/model field is required, mark CONTRACT CHANGE here and only update the specific media_v2 model + test files listed.  
- If additional files appear necessary, STOP and report; do not refactor outside the allow-list.

## 5. Implementation checklist (mechanical)  
- Design CadGanttView/CadOverlayView Pydantic models: task_id, label/title, trade, start_date, end_date/duration, predecessors (with types), level/zone, quantity/unit, cost, source_kind/source_id, hash/meta, tenant_id/env/request_id.  
- Define mapping rules:  
  - cad_semantics + plan_of_work → CadGanttView (tasks + dependencies, grouping by trade/level/zone, dates, status).  
  - cad_semantics + boq_quantities + cost_model → CadOverlayView (elements/rooms with quantity/unit/cost, grouping by level/zone/trade).  
- Deterministic hash strategy: derive view-model hashes/IDs from upstream artifact hashes + version and grouping fields.  
- Implement cad_viewer.service functions: load artifacts for project_id/cad_model_id; build view-models in memory; no writes.  
- Implement cad_viewer.routes endpoints:  
  - GET /cad/viewer/{project_id}/gantt → CadGanttView JSON  
  - GET /cad/viewer/{project_id}/overlays → CadOverlayView JSON  
  - Propagate tenant_id/env/request_id via RequestContext; echo in meta; leave auth unchanged.

## 6. Tests  
- engines/cad_viewer/tests/test_gantt_view.py: small fixture project → tasks with correct dates/dependencies/trades and deterministic hashes; clear error when artifacts missing.  
- engines/cad_viewer/tests/test_overlay_view.py: wall/room fixtures → correct quantity and cost aggregation per element/zone/trade; deterministic hashes; missing artifacts produce clear errors/404 without partial data.  
- engines/media_v2/tests/test_validation_strict_cad_viewer.py (only if CONTRACT CHANGE): validate any registered view-model artifact kinds/meta.  
- Determinism and scope are mandatory assertions in all tests.

## 7. Docs & examples  

### Data Flow  
```
CAD01–05 engines → plan_of_work/boq_costing models → cad_viewer.service → CadGanttView / CadOverlayView JSON → TL01 / Generic UI
```

**Service Integration:**
- CAD viewer integrates directly with plan_of_work.service (via `generate_plan(cost_model_id)`)
- CAD viewer integrates directly with boq_costing.service (via `get_cost_model(cost_model_id)`)
- Deterministic hashing: SHA256 of ordered model hashes + identifiers (no external artifact store required)

### Example 1: Small House  

**Input Plan & Cost Model:**
- Cost Model ID: `cost_model_house_v1`
- Plan Service generates: PlanOfWork with 2 tasks (Excavate: 4 days, Foundation: 4 days)
- Costing Service provides: 2 items (Wall: 50m2 @ $50k, Floor: 100m2 @ $50k)

**Expected CadGanttView JSON:**
```json
{
  "project_id": "proj_house_001",
  "cad_model_id": "cost_model_house_v1",
  "tasks": [
    {
      "id": "task-1",
      "name": "Excavate",
      "trade": "foundation",
      "level": "L1",
      "zone": "Z1",
      "start_date": null,
      "end_date": null,
      "duration_days": 4.0,
      "predecessors": [],
      "refs": [],
      "meta": {},
      "hash": "sha256_deterministic_hash_1"
    },
    {
      "id": "task-2",
      "name": "Foundation",
      "trade": "foundation",
      "level": "L1",
      "zone": "Z1",
      "start_date": null,
      "end_date": null,
      "duration_days": 4.0,
      "predecessors": ["task-1"],
      "refs": [],
      "meta": {},
      "hash": "sha256_deterministic_hash_2"
    }
  ],
  "meta": {
    "source_engine": "plan_of_work",
    "plan_model_hash": "plan_house_hash_v1",
    "request_context": {
      "tenant_id": "tenant_house",
      "env": "dev",
      "request_id": "req_12345"
    }
  },
  "view_hash": "view_hash_gantt_house_deterministic"
}
```

**Expected CadOverlayView JSON:**
```json
{
  "project_id": "proj_house_001",
  "cad_model_id": "cost_model_house_v1",
  "elements": [
    {
      "id": "item-1",
      "name": "Exterior Wall",
      "level": "L1",
      "zone": "Z1",
      "trade": "unknown",
      "quantity": 50.0,
      "unit": "m2",
      "cost": 50000.0,
      "hash": "sha256_deterministic_hash_element_1",
      "meta": {}
    },
    {
      "id": "item-2",
      "name": "Floor Slab",
      "level": "L1",
      "zone": "Z1",
      "trade": "unknown",
      "quantity": 100.0,
      "unit": "m2",
      "cost": 50000.0,
      "hash": "sha256_deterministic_hash_element_2",
      "meta": {}
    }
  ],
  "meta": {
    "source_engine": "boq_costing",
    "cost_model_hash": "cost_house_hash_v1",
    "request_context": {
      "tenant_id": "tenant_house",
      "env": "dev",
      "request_id": "req_12345"
    }
  },
  "view_hash": "view_hash_overlay_house_deterministic"
}
```

### Example 2: Small Extension  

**Input Plan & Cost Model:**
- Cost Model ID: `cost_model_extension_v1`
- Plan Service generates: PlanOfWork with 3 tasks (Demolition: 2 days, Framing: 10 days, Finishes: 12 days)
- Costing Service provides: 3 items (Demo work, Frame work, Finish work)

**Expected CadGanttView JSON (excerpt):**
```json
{
  "project_id": "proj_extension_001",
  "cad_model_id": "cost_model_extension_v1",
  "tasks": [
    {
      "id": "task-1",
      "name": "Demolition Prep",
      "trade": "foundation",
      "level": "L1",
      "zone": "Z1",
      "duration_days": 2.0,
      "predecessors": [],
      "hash": "deterministic_hash_dem"
    },
    {
      "id": "task-2",
      "name": "Framing",
      "trade": "foundation",
      "level": "L1",
      "zone": "Z1",
      "duration_days": 10.0,
      "predecessors": ["task-1"],
      "hash": "deterministic_hash_frame"
    },
    {
      "id": "task-3",
      "name": "Finishes",
      "trade": "foundation",
      "level": "L1",
      "zone": "Z1",
      "duration_days": 12.0,
      "predecessors": ["task-2"],
      "hash": "deterministic_hash_finish"
    }
  ],
  "view_hash": "view_hash_gantt_extension_deterministic"
}
```

### Schema Summary  

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| **CadGanttView** | | | |
| project_id | string | Yes | Project identifier |
| cad_model_id | string | Yes | Cost model ID (logical entry point) |
| tasks | List[GanttTask] | Yes | Array of scheduled tasks from plan_of_work |
| meta | Dict | Yes | source_engine, plan_model_hash, request_context |
| view_hash | string | Yes | Deterministic hash of entire view |
| | | | |
| **GanttTask** | | | |
| id | string | Yes | Task ID from PlanTask |
| name | string | Yes | Task name |
| trade | string | Yes | Category from PlanTask (foundation, structure, etc.) |
| level | string | Yes | Building level (default L1, refined by CAD06+) |
| zone | string | Yes | Project zone (default Z1, refined by CAD06+) |
| start_date | string &#124; null | No | ISO 8601 date (computed from early_start_day in CAD06+) |
| end_date | string &#124; null | No | ISO 8601 date (computed from early_finish_day in CAD06+) |
| duration_days | float | Yes | Duration in days |
| predecessors | List[string] | Yes | Task IDs of immediate predecessors (may be empty) |
| refs | List[string] | Yes | Additional references (may be empty) |
| meta | Dict | Yes | Task metadata (may be empty) |
| hash | string | Yes | Deterministic task hash |
| | | | |
| **CadOverlayView** | | | |
| project_id | string | Yes | Project identifier |
| cad_model_id | string | Yes | Cost model ID |
| elements | List[OverlayElement] | Yes | Array of elements from cost model items |
| meta | Dict | Yes | source_engine, cost_model_hash, request_context |
| view_hash | string | Yes | Deterministic hash of entire view |
| | | | |
| **OverlayElement** | | | |
| id | string | Yes | Item ID from CostItem |
| name | string | Yes | Item name |
| level | string | Yes | Building level (default L1) |
| zone | string | Yes | Project zone (default Z1) |
| trade | string | Yes | Trade/category from CostItem |
| quantity | float | Yes | Quantity from CostItem |
| unit | string | Yes | Unit of measure (m2, count, etc.) |
| cost | float | Yes | Total cost from CostItem |
| hash | string | Yes | Deterministic element hash |
| meta | Dict | Yes | Element metadata (may be empty) |

### Determinism Guarantee  
- All hashes (task_hash, element_hash, view_hash) are deterministically derived from:
  - Upstream model hashes (plan.model_hash, cost_model.model_hash)
  - Task/element identifiers and key fields (id, name, duration_days, quantity, unit, cost)
  - Ordered concatenation of fields followed by SHA256 hashing
- Same input models always produce identical JSON and hashes; view-models are immutable once generated.

### Testing Strategy
- `test_gantt_view.py`: Mock plan_of_work service; verify task structure, dependencies, deterministic hashes, error handling
- `test_overlay_view.py`: Mock boq_costing service; verify element aggregation, quantity/cost exposure, deterministic hashes, error handling
- Both test suites verify:
  - Determinism (same input → same hash)
  - Scope (read-only, no mutations)
  - Error clarity (MissingArtifactError when service returns None)
  - RequestContext propagation

## 8. Execution note  
Workers must complete code + tests + docs strictly within the allow-list to meet the DoD. If any work seems to require files outside the list, STOP and report. Once DoD and tests are satisfied, PHASE_VIEW01 is DONE; later phases (CAD06–08) may extend overlays without breaking these contracts.
