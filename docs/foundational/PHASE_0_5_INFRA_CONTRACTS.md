# Phase 0.5 — Infra Contracts (Engines Control-Plane + Stream Events)

**Audience:** UI (atoms-factory), Graph/Agents teams. This document specifies the stable contracts that engines exposes for routing, events, and infra mutations.

**Invariant:** All control-plane operations emit audit + stream events with canonical RequestContext routing keys so UI can safely render config changes and timeline replay.

---

## Part 1: Control-Plane API (Routing Registry)

All endpoints require RequestContext headers:

```
X-Tenant-Id: t_demo           (required)
X-Mode: saas|enterprise|lab   (required)
X-Project-Id: p_internal      (optional, defaults to p_internal)
X-App-Id: app_name            (optional)
X-Surface-Id: surface_name    (optional; aliases accepted, stored canonical)
X-Request-Id: uuid            (optional, auto-generated if missing)
```

### POST /routing/routes

**Upsert a routing entry.**

Request:
```json
{
  "resource_kind": "object_store",
  "tenant_id": "t_demo",
  "env": "dev",
  "project_id": "p_internal",
  "backend_type": "filesystem",
  "config": {
    "base_dir": "var/object_store"
  },
  "required": true
}
```

Response (201):
```json
{
  "id": "uuid",
  "resource_kind": "object_store",
  "tenant_id": "t_demo",
  "env": "dev",
  "project_id": "p_internal",
  "surface_id": null,
  "backend_type": "filesystem",
  "config": {"base_dir": "var/object_store"},
  "required": true,
  "created_at": "2026-01-02T12:34:56Z",
  "updated_at": "2026-01-02T12:34:56Z"
}
```

**Emits:**
- ROUTE_CHANGED stream event (see Part 2)
- routing:upsert audit event

---

### GET /routing/routes/{resource_kind}/{tenant_id}/{env}

**Get a routing entry by resource_kind/tenant/env.**

Query params:
```
?project_id=p_internal  (optional)
```

Response (200):
```json
{
  "id": "uuid",
  "resource_kind": "object_store",
  ...
}
```

Response (404): Route not found

---

### GET /routing/routes

**List routes with optional filters.**

Query params:
```
?resource_kind=object_store   (optional)
?tenant_id=t_demo             (optional)
```

Response (200):
```json
[
  {
    "id": "uuid",
    "resource_kind": "object_store",
    ...
  }
]
```

---

## Part 2: Stream Events (Timeline)

All domain actions emit `StreamEvent` using canonical envelope.

### StreamEvent Structure

```python
{
  "v": 1,
  "type": "EVENT_TYPE",  # e.g. ROUTE_CHANGED, EVENT_STREAM_APPEND, OBJECT_STORE_PUT
  "ts": "2026-01-02T12:34:56.123Z",
  "event_id": "uuid",
  
  # Routing keys (tenant/mode/project/app/surface/actor)
  "routing": {
    "tenant_id": "t_demo",
    "mode": "saas",
    "env": "dev",
    "project_id": "p_internal",
    "app_id": "app_name",
    "surface_id": "squared2",  # normalized canonical form
    "actor_id": "user_123 or system",
    "actor_type": "human|agent|system",
    "thread_id": null,
    "canvas_id": null,
    "session_id": null,
    "device_id": null
  },
  
  # Request context IDs
  "ids": {
    "request_id": "uuid",
    "trace_id": "uuid",
    "run_id": null,
    "step_id": null
  },
  
  # Domain-specific data
  "data": {
    "action": "...",
    "resource_kind": "...",
    ...
  },
  
  # Metadata
  "meta": {
    "schema_ver": "1",
    "priority": "truth|gesture|info",
    "persist": "always|sampled|never",
    "severity": "info|warning|error"
  }
}
```

**Appended to stream:** `{resource_kind or "infra"}/{tenant_id}` (e.g., `routing/t_demo`)

---

### Event Types (Lane 2+3 domains)

#### ROUTE_CHANGED
Emitted when routing registry is mutated (upsert).

```json
{
  "type": "ROUTE_CHANGED",
  "data": {
    "action": "upsert|delete",
    "resource_kind": "object_store",
    "backend_type": "filesystem|s3|firestore",
    "route_id": "uuid"
  }
}
```

---

#### EVENT_STREAM_APPEND
Emitted when a timeline event is appended (any event in timeline).

```json
{
  "type": "EVENT_STREAM_APPEND",
  "data": {
    "action": "append",
    "stream_id": "thread_123 or canvas_456",
    "appended_event_id": "uuid",
    "appended_event_type": "message|gesture|canvas_command"
  }
}
```

Persisted to: `event_stream/{tenant_id}`

---

#### OBJECT_STORE_PUT
Emitted when a blob is stored.

```json
{
  "type": "OBJECT_STORE_PUT",
  "data": {
    "action": "put",
    "key": "artifact_uuid/filename.pdf",
    "size_bytes": 10240,
    "content_type": "application/pdf"
  }
}
```

Persisted to: `object_store/{tenant_id}`

---

#### TABULAR_UPSERT
Emitted when a policy/hard-fact record is upserted.

```json
{
  "type": "TABULAR_UPSERT",
  "data": {
    "action": "upsert",
    "table_name": "policies",
    "record_key": "policy_shopify_returns",
    "timestamp": "2026-01-02T12:34:56Z"
  }
}
```

Persisted to: `tabular_store/{tenant_id}`

---

#### METRIC_INGEST
Emitted when a raw metric data point is ingested.

```json
{
  "type": "METRIC_INGEST",
  "data": {
    "action": "ingest",
    "metric_name": "weekly_leads",
    "value": 42,
    "tags": {"campaign": "acme_q1"}
  }
}
```

Persisted to: `metrics_store/{tenant_id}`

---

## Part 3: Routing Key Rules

### Surface ID Normalization

**Problem:** UI may pass `SQUARED²` or `squared` but engines stores canonical `squared2`.

**Rule 1: Aliases accepted everywhere**
- Incoming headers/bodies accept: `squared`, `squared2`, `SQUARED`, `SQUARED2`, `SQUARED²`, etc.
- Normalizer maps all variants → `squared2` (canonical ASCII)

**Rule 2: Stored form is always canonical**
- `response.surface_id` always `squared2`
- Filesystem paths use canonical form
- No ambiguity in replay/replay

**Rule 3: Stream events use canonical form**
- `event.routing.surface_id = "squared2"` (never the alias)
- Timeline replay shows correct form

---

### Stream ID Formation

**For chat/canvas services (existing):**
```
stream_id = thread_id           (chat messages)
stream_id = canvas_id           (canvas events/gestures)
```

**For infra services (new):**
```
stream_id = "{resource_kind}/{tenant_id}"
  examples:
  - "event_stream/t_demo"
  - "object_store/t_demo"
  - "metrics_store/t_demo"
```

---

## Part 4: Timeline Replay (SSE + Last-Event-ID)

**SSE endpoint:** `/sse/stream/{stream_id}`

**Request with replay:**
```
GET /sse/stream/thread_abc?Last-Event-ID=event_uuid_456
```

**Response:** Server streams all events after `event_uuid_456` in append order, followed by new events.

**Guarantee:**
- Events persisted via routing registry to filesystem/firestore survive restart.
- On reconnect, Last-Event-ID triggers replay from that point.
- All domain actions (ROUTE_CHANGED, EVENT_STREAM_APPEND, OBJECT_STORE_PUT, etc.) appear in stream in order.

---

## Part 5: Filesystem Layout (Dev/Local)

All filesystem adapters use deterministic directory structure under `var/`:

```
var/
├── routing/
│   ├── {resource_kind}/
│   │   ├── {tenant_id}/
│   │   │   ├── {env}/
│   │   │   │   └── {project_id or "_"}.json
├── event_stream/
│   ├── {tenant_id}/
│   │   ├── {env}/
│   │   │   ├── {surface_id or "_"}/
│   │   │   │   ├── thread_abc/events.jsonl
│   │   │   │   ├── canvas_def/events.jsonl
├── object_store/
│   ├── {tenant_id}/
│   │   ├── {env}/
│   │   │   ├── {surface_id or "_"}/
│   │   │   │   ├── blobs/
│   │   │   │   │   ├── artifact_uuid.bin
│   │   │   │   │   ├── media_xyz.pdf
├── tabular_store/
│   ├── {tenant_id}/
│   │   ├── {env}/
│   │   │   ├── {surface_id or "_"}/
│   │   │   │   ├── policies.jsonl
│   │   │   │   ├── settings.jsonl
├── metrics_store/
│   ├── {tenant_id}/
│   │   ├── {env}/
│   │   │   ├── {surface_id or "_"}/
│   │   │   │   ├── raw.jsonl
```

**Note:** `{surface_id or "_"}` means:
- If surface_id provided: use normalized canonical form (e.g., `squared2`)
- If not provided: use `_` as placeholder

---

## Part 6: No-Breaking Changes to Existing Contracts

- Existing timeline interfaces unchanged (append/list_after)
- Existing object_store services (raw_storage) upgraded to use routing but maintain API
- New tabular/metrics services added without touching existing KPI/budget models
- Surface normalizer applied transparently in routing lookups

---

## Migration Path (from env-driven to routing)

**Old way:**
```bash
export STREAM_TIMELINE_BACKEND=firestore
```

**New way:**
```bash
# Create route
curl -X POST http://localhost:8010/routing/routes \
  -H 'Content-Type: application/json' \
  -d '{"resource_kind":"event_stream","tenant_id":"t_system","env":"dev","backend_type":"firestore"}'

# Engine starts, resolves via routing, uses Firestore
```

**For dev (filesystem default):**
```bash
# Create route
curl -X POST http://localhost:8010/routing/routes \
  -d '{"resource_kind":"event_stream","tenant_id":"t_system","env":"dev","backend_type":"filesystem"}'

# Everything persisted to var/event_stream/... (survives restart)
```

---

## API Error Codes

| Code | Meaning |
|------|---------|
| 200  | Success (GET/LIST) |
| 201  | Created (POST upsert) |
| 400  | Invalid request (bad tenant_id format, missing required field) |
| 403  | Forbidden (strategy lock/role guard, if applied) |
| 404  | Not found (route missing, blob not found) |
| 500  | Server error (backend unavailable, disk full, etc.) |

---

## Summary for UI/Atoms Teams

✅ All infra mutations (routing, object storage, policy upserts, metrics ingests) emit StreamEvents.

✅ Stream events use canonical RequestContext routing keys + surface normalization.

✅ Timeline replay via Last-Event-ID includes all domain actions.

✅ Filesystem layout is deterministic and documented.

✅ Surface aliases (SQUARED², squared, etc.) are normalized transparently; no branching in UI.

✅ No env-driven logic; routing registry is the single source of truth for backend selection.
