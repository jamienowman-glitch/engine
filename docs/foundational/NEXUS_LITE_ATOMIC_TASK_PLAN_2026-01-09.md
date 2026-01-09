# Nexus Lite (LanceDB) — Merged Atomic Task Plan

**Date:** 2026-01-09
**Goal:** Production-ready “Nexus Lite” (tenant-isolated RAG store) using LanceDB on object storage, with global-per-surface and canonical 503/410 envelopes.

## Non-negotiable contract baked in (must be implemented in P0)

### SpaceKey (storage + routing identity)

A “space” is addressed by:

`SpaceKey = {scope, tenant_id, env/mode, project_id, surface_id, space_id}`

*   `scope=tenant` → `tenant_id = RequestContext.tenant_id` (read/write)
*   `scope=global` → `tenant_id = "t_system"` (read-only for normal tenants; write only for system/admin)
*   `surface_id` MUST be part of the key (so “global marketing” ≠ “global health”)
*   `include_global=true` means query:
    1.  tenant space
    2.  global space for the caller’s `surface_id`
    and then merge results with a `source_scope` tag.

### Canonical errors
*   Missing route → **503** with `error.code = nexus_store.missing_route` (or `nexus_blob_store.missing_route`)
*   Invalid cursor → **410** with `error.code = nexus.cursor_invalid`

---

## /northstar-engines (P0)

### TASK-E-00 — Lock SpaceKey + global-per-surface behavior in code (tiny but critical)
*   **Files:** `engines/nexus/schemas.py` (or nearest nexus schema module), plus any Nexus config/constants module you already use.
*   **Action:** Define a single internal helper/dataclass for `SpaceKey` that includes:
    `tenant_id`, `env/mode`, `project_id`, `surface_id`, `space_id`, `scope(tenant|global)`
*   **Criteria:** All store open/query paths use this helper (no ad-hoc path building).

### TASK-E-01 — Add core dependencies
*   **Files:** `pyproject.toml` (or `requirements.txt`)
*   **Action:** Add `lancedb`, `fsspec`, plus cloud drivers:
    *   `s3fs`, `gcsfs`, `adlfs`
*   **Tests:** add/extend a tiny import test (where your repo keeps these)
*   **Criteria:** deps install; imports succeed.

### TASK-E-02 — Define routing resource kinds + signals
*   **Files:**
    *   `engines/nexus/signals.py` (NEW) — define `IngestRequest` (pydantic) event payload
    *   `engines/routing/resource_kinds.py` — add:
        *   `NEXUS_STORE = "nexus_store"`
        *   `NEXUS_BLOB_STORE = "nexus_blob_store"`
*   **Criteria:** resource kind constants exist and are used by the service layer.

### TASK-E-03 — Implement LanceVectorStore (tenant isolated + global-per-surface)
*   **Files:** `engines/nexus/lance_store.py` (NEW)
*   **Resource_kind:** `nexus_store` (backend type `lancedb`)
*   **Action:**
    *   Implement the existing `NexusVectorStore` protocol (reusing any interface already present).
    *   Path scheme MUST include `project_id` + `surface_id`:
        *   `{root}/{tenant_id}/{env_or_mode}/{project_id}/{surface_id}/{space_id}.lance`
    *   Global store uses `tenant_id="t_system"` and same `surface_id` as caller.
    *   Cursor paging for query results:
        *   Cursor must be deterministic and restart-safe.
        *   Unknown/invalid cursor → **410** `nexus.cursor_invalid` envelope.
*   **Tests:** `engines/nexus/tests/test_lance_store.py`
*   **Criteria:**
    *   Tenant isolation test: tenant A sees A, tenant B sees nothing.
    *   Restart-safe: write → re-init store → read.
    *   Global-per-surface: marketing global does not appear in health queries.

### TASK-E-04 — Add nexus_blob_store wrapper (fsspec)
*   **Files:** `engines/nexus/blob_store.py` (NEW) (or under `engines/storage` if that’s your pattern)
*   **Resource_kind:** `nexus_blob_store`
*   **Action:**
    *   Provide a minimal blob API: `put_bytes`, `get_bytes`, `exists`, `resolve_uri`
    *   Must route via routing registry; missing route → **503** envelope.
*   **Tests:** `engines/nexus/tests/test_blob_store_routing.py`
*   **Criteria:** portable local/S3/GCS/Azure path support via `fsspec`, routed only.

### TASK-E-05 — Nexus HTTP endpoints (ingest + query)
*   **Files:**
    *   `engines/nexus/service.py` (create or update)
    *   `engines/nexus/routes.py`
*   **Endpoints:**
    *   `POST /nexus/spaces/{space_id}/ingest` → 202 `{task_id}`
    *   `POST /nexus/spaces/{space_id}/query` → `{hits, next_cursor}`
*   **Behavior:**
    *   Route lookup for `nexus_store` required:
        *   missing route → **503** `nexus_store.missing_route`
    *   Query validates cursor:
        *   invalid cursor → **410** `nexus.cursor_invalid`
    *   `include_global=true` merges tenant + global-per-surface results and adds `source_scope` per hit.
*   **Tests:** `engines/nexus/tests/test_api_routing.py`
*   **Criteria:** 503/410 envelopes are canonical; results include source tag when merged.

### TASK-E-06 — Ingestion worker via Event Spine (no always-on DB)
*   **Files:** `engines/nexus/worker.py` (NEW)
*   **Action:**
    *   Ingest endpoint emits an Event Spine event (e.g. `nexus.ingest_requested`) using `IngestRequest`.
    *   Worker consumes events and:
        *   resolves blob refs (if any)
        *   produces embeddings via an adapter (stub allowed P0 if embeddings already exist elsewhere)
        *   upserts into Lance store
*   **Tests:** `engines/nexus/tests/test_ingest_flow.py`
*   **Criteria:** event emission leads to a row appearing in Lance (eventual consistency).

### TASK-E-07 — Global permissions
*   **Files:** `engines/nexus/service.py` (and auth dependency module if needed)
*   **Action:**
    *   Enforce: writes to `scope=global` require privileged system/admin OR `tenant_id == "t_system"`
    *   Normal tenants can only read global when `include_global=true`
*   **Tests:** `engines/nexus/tests/test_global_permissions.py`
*   **Criteria:** global writes blocked for normal tenants; reads allowed only via `include_global`.

### TASK-E-08 — P0 integration tests (acceptance criteria)
*   **Files:** `engines/nexus/tests/test_nexus_p0_acceptance.py` (or split tests)
*   **Must assert:**
    1.  Restart server → tenant space persists
    2.  Missing `nexus_store` route → 503 `nexus_store.missing_route`
    3.  Invalid cursor → 410 `nexus.cursor_invalid`
    4.  Tenant A cannot read Tenant B
    5.  `include_global` merges tenant + global per surface (no cross-surface bleed)
    6.  No always-on vector DB (Lance runs in-process; worker is just a consumer process)

---

## /northstar-engines (P1 / P2)

### TASK-E-09 (P1) — Global fusion ranking + filtering
*   Better merge policy, per-source caps, optional rerank hook.

### TASK-E-10 (P2) — KPI Fact Generator
*   **File:** `engines/kpi/fact_worker.py` (NEW)
*   Reads KPI raw measurements, emits ingest events of `type="kpi"`.

### TASK-E-11 (P2) — HAZE adapter
*   Abstract explorer away from Vertex and add Lance-backed points endpoint/snapshot.

---

## /northstar-agents (P1)

### TASK-A-01 — Nexus client
*   **Files:** `src/northstar/clients/nexus.py` (NEW)
*   **Action:** Minimal wrapper for:
    *   `POST /nexus/spaces/{space_id}/query`
    *   `POST /nexus/spaces/{space_id}/ingest`
*   **Tests:** `tests/test_nexus_client.py`
*   **Criteria:** propagates canonical envelope codes; no coupling to static cards.

---

## /ui (P2)

### TASK-U-01 — Haze viewer wiring
*   **Files:** `agentflow/components/haze/HazeViewer.tsx`
*   **Action:** swap to `/nexus/spaces/{id}/haze/points` when that exists.

---

## Acceptance Criteria (verbatim, updated)

1.  Restart server → tenant space data persists
2.  Missing route for `nexus_store` → **503** canonical envelope (`nexus_store.missing_route`)
3.  Invalid cursor → **410** canonical envelope (`nexus.cursor_invalid`)
4.  Tenant A cannot read Tenant B (RequestContext isolation)
5.  `include_global=true` queries tenant + `t_system` global for the same `surface_id`, merges with `source_scope` tag, no leakage
6.  No always-on vector DB process (Lance is file-backed; worker is event consumer)
