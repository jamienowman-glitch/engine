# Agnostic Timeline Engine (TL01)

The Agnostic Timeline Engine provides a centralized, domain-agnostic service for managing project schedules. It allows various inputs (CAD construction plans, marketing content calendars, etc.) to be normalized into a common task/dependency model and visualized via a standard Gantt view.

## Core Concepts

### Models (`engines/timeline_core/models.py`)

- **Task**: A unit of work with a `start_ts` and `end_ts` (and/or `duration_ms`).
    - **Deterministic ID**: Generated from `hash(tenant|env|source_kind|source_id)` for idempotent updates.
    - **Grouping**: `group_id` (e.g. Campaign/Floor) and `lane_id` (e.g. Channel/Trade) support Gantt hierarchies.
- **Dependency**: Links two tasks (`from_task_id` -> `to_task_id`). Standard `FINISH_TO_START` supported.
- **GanttView**: A read-only projection of tasks into a hierarchical format (`Rows` -> `Sub-Rows` -> `Items`).

### Service (`engines/timeline_core/service.py`)

- **CRUD**: Create, read, update, delete tasks and dependencies.
- **Adapters**:
    - `import_from_plan_of_work`: Ingests CAD `PlanOfWork` objects.
    - `import_from_boq`: Ingests CAD `BoQModel` objects.
    - `import_from_content_plan`: Ingests Marketing `ContentPlanPayload`.
- **Validation**: Enforces `start <= end`, cycle detection, and tenant isolation.

## API Usage (`engines/timeline_core/router.py`)

The engine exposes a FastAPI router at `/timeline`.

### 1. Create a Task
```bash
curl -X POST "http://localhost:8000/timeline/tasks" \
  -H "X-Tenant-Id: t_demo" \
  -H "X-Env: dev" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "t_demo",
    "env": "dev",
    "request_id": "req-001",
    "title": "Foundation Work",
    "start_ts": "2025-01-01T09:00:00Z",
    "end_ts": "2025-01-05T17:00:00Z",
    "group_id": "Phase 1",
    "lane_id": "Construction"
  }'
```

### 2. Add a Dependency
```bash
curl -X POST "http://localhost:8000/timeline/dependencies" \
  -H "X-Tenant-Id: t_demo" \
  -H "X-Env: dev" \
  -d '{
    "from_id": "parent-task-id",
    "to_id": "child-task-id"
  }'
```

### 3. Get Gantt View
```bash
curl -X GET "http://localhost:8000/timeline/view/gantt" \
  -H "X-Tenant-Id: t_demo" \
  -H "X-Env: dev"
```
**Response:**
```json
{
  "project_start": "2025-01-01T09:00:00Z",
  "project_end": "2025-01-05T17:00:00Z",
  "rows": [
    {
      "id": "Phase 1",
      "label": "Phase 1",
      "sub_rows": [
        {
          "id": "Construction",
          "label": "Construction",
          "items": [
            {
              "id": "...",
              "label": "Foundation Work",
              "start": "2025-01-01T09:00:00+00:00",
              "end": "2025-01-05T17:00:00+00:00",
              "dependencies": []
            }
          ]
        }
      ]
    }
  ]
}
```

## Running Tests

```bash
# Models & Validation
python3 -m pytest engines/timeline_core/tests/test_validation.py

# Service Logic & Adapters
python3 -m pytest engines/timeline_core/tests/test_service.py

# API Router
python3 -m pytest engines/timeline_core/tests/test_router.py
```
