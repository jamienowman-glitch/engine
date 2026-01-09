# Nexus Lite (LanceDB) Contract

**Date:** 2026-01-09
**Status:** DRAFT (Locked for Implementation)
**Author:** Architect Recon Agent

## 1. Terminology

| Term | Definition |
|---|---|
| **Space** | A logical container for knowledge, strictly isolated by tenant + environment. Two types: **Tenant Space** (read/write, private) and **Global Space** (read-only, shared/system). |
| **Document** | A unit of knowledge (text chunk, image ref, or KPI fact). |
| **Chunk** | A subdivision of a document for vectorization (if text). |
| **MediaRef** | A pointer to a blob (image/video) stored in `nexus_blob_store`, with an associated embedding. |
| **KPI Fact Doc** | A synthesized text document describing a KPI state/trend (derived from `engines.kpi`), ingested for RAG. |
| **Embedding** | Vector representation (768d or similar). Model Provider can be **Local** (CPU/ONNX) or **Remote** (Vertex/OpenAI). |
| **Query** | A semantic search request yielding ranked `VectorHit` results. |

## 2. Storage & Routing

We introduce **Nexus Lite** as a durable, portable knowledge layer using **LanceDB** on Object Storage.

### 2.1 Resource Kinds
New entries in `engines.routing.registry`:

*   **`nexus_store`**: The LanceDB dataset location.
    *   **Backend:** `lancedb`
    *   **Config:** `{ "uri": "s3://...", "table_name": "vectors" }` (or local path for dev).
*   **`nexus_blob_store`**: Raw object storage for media files.
    *   **Backend:** `fsspec` (s3/gcs/az)
    *   **Config:** `{ "protocol": "s3", "bucket": "...", "prefix": "media/" }`
*   **`nexus_projection_store`** (Optional/Later): For HAZE pre-computed items (UMAP/TSNE json).

### 2.2 Behavior Rules
*   **Missing Route**: If `nexus_store` is not configured for a tenant, raise **503 Service Unavailable**:
    ```json
    { "error": { "code": "nexus_store.missing_route", "resource_kind": "nexus_store", ... } }
    ```
*   **Invalid Cursor**: If a pagination cursor is stale/corrupt, raise **410 Gone**:
    ```json
    { "error": { "code": "nexus.cursor_invalid", ... } }
    ```
*   **Isolation**: All reads/writes MUST use `tenant_id` from `RequestContext`. **Cross-tenant access is strictly forbidden** at the code level. Global space reads are verified via explicit `include_global=True` flag and separate routing lookup.

## 3. Canonical Endpoints (Engines)

All endpoints return canonical `ErrorEnvelope` on failure.

### 3.1 Ingest
`POST /nexus/spaces/{space_id}/ingest`
Buffered async ingestion.
**Request:**
```json
{
  "items": [
    { "type": "text", "content": "...", "metadata": { "source": "doc1" } },
    { "type": "image", "blob_path": "s3://...", "metadata": { "source": "pinterest" } }
  ]
}
```
**Response:** `202 Accepted` `{ "task_id": "..." }`

### 3.2 Query
`POST /nexus/spaces/{space_id}/query`
**Request:**
```json
{
  "q": "agents with blue eyes",
  "filters": { "source": "pinterest" },
  "top_k": 10,
  "include_global": true,
  "cursor": null
}
```
**Response:**
```json
{
  "hits": [
    { "doc_id": "...", "score": 0.89, "content": "...", "metadata": {} }
  ],
  "next_cursor": "..."
}
```

### 3.3 HAZE Extensions (Optional)
*   `GET /nexus/spaces/{space_id}/haze/points` (Stream points for visualization)
*   `POST /nexus/spaces/{space_id}/haze/snapshot` (Trigger re-projection)

## 4. LanceDB Backing Contract

**Library:** `lancedb` (Python).
**Storage Adapter:** `fsspec` (with `s3fs`, `gcsfs`, or `adlfs`).

### 4.1 Path Scheme
Structure storage to allow easy localized mounting or cloud sync.
`{root}/{tenant_id}/{project_id}/{space_id}.lance`

**Examples:**
*   Local: `/var/data/nexus/t_acme/default/main.lance`
*   S3: `s3://my-bucket/nexus/t_acme/default/main.lance`

### 4.2 Schema (Minimal)
```python
class NexusSchema(pa.Schema):
    id: str
    vector: vector(768)
    text: str
    type: str  # text | image | kpi
    metadata: str  # JSON string
    timestamp: timestamp
```

## 5. Deployment & Identity

*   **Identity**: `RequestContext` is the source of truth.
*   **Provider**: `EmbeddingProvider` interface in Engines must support:
    *   `LocalProvider` (SentenceTransformers, run on CPU/GPU worker).
    *   `RemoteProvider` (OpenAI/Vertex, verify billing via `gates`).

## 6. KPI Fact Docs

**Flow:**
1.  **Source**: `engines.kpi` (raw measurements).
2.  **Trigger**: Periodic worker or "End of Run" event.
3.  **Transform**: `KPIFactWorker` reads measurements, generates natural language summary (e.g., "Latency increased by 20% in the last hour").
4.  **Ingest**: Pushes text to `nexus_store` with `type="kpi"`.

This allows Agents to ask "How is performance?" and get RAG answers based on real data.
