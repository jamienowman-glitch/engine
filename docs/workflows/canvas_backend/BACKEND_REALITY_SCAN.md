# Backend Reality Scan (Northstar Engines)

**Date:** 2025-12-16
**Scope:** Realtime, Canvas, Artifacts, Auth, Storage

## 1. Transports & Protocols

### WebSocket (`engines/chat/service/ws_transport.py`)
*   **Status:** Exists.
*   **Path:** `/ws/chat/{thread_id}`
*   **Auth:** Query param `token` or "anon" fallback. manual JWT decode.
*   **Isolation:** **WEAK**. Checks auth token validity but assumes thread access if token is valid. No explicit `validate_routing` or database check for `thread_id` ownership.
*   **Heartbeat:** Exists (30s interval).
*   **Protocol:** JSON messages `{type: "message", ...}`. No `StreamEvent` standard.

### SSE Chat (`engines/chat/service/sse_transport.py`)
*   **Status:** Exists.
*   **Path:** `/sse/chat/{thread_id}`
*   **Auth:** Headers `Authorization`.
*   **Isolation:** **WEAK**. Checks `auth_context.default_tenant_id` matches `request_context.tenant_id`, but does NOT verify `thread_id` belongs to that tenant.
*   **Replay:** Supports `Last-Event-ID`.

### SSE Canvas (`engines/canvas_stream/router.py`)
*   **Status:** Exists.
*   **Path:** `/sse/canvas/{canvas_id}`
*   **Auth:** Uses `get_auth_context`.
*   **Isolation:** **MISSING**. Contains explicit `TODO: Verify canvas_id belongs to tenant_id`.
*   **Payload:** Unwraps `msg.text` JSON manually ("Message.text JSON" hack).

## 2. Event Contracts

### Current Schema (`engines/chat/contracts.py`)
*   **Model:** `Message`
*   **Fields:** `id`, `thread_id`, `sender`, `text`, `role`, `scope`.
*   **Gap:** No `type`, `seq`, `tracing`, or structured `data`. Everything is flattened into `text` (JSON string) or ad-hoc dicts.
*   **Action:** Needs replacing/wrapping with `StreamEvent`.

## 3. Auth & Identity (`engines/common/identity.py`)
*   **RequestContext:** Exists. Validates `tenant_id` regex `t_*`.
*   **Gap:** `get_request_context` trusts headers/query params mostly. Real JWT integration is partial/stubbed in some places.

## 4. Storage & Artifacts

### Raw Storage (`engines/nexus/raw_storage`)
*   **S3 Repo:** `engines/nexus/raw_storage/repository.py`
*   **Pathing:** `tenants/{tenant_id}/{env}/raw/{asset_id}/{filename}`
*   **Compliance:** **HIGH**. Matches spec exactly.

### Media V2 (`engines/media`)
*   **GCS Client:** `engines/storage/gcs_client.py`
*   **Pathing:** `{tenant_id}/media/{path}`
*   **Gap:** Missing `tenants/` prefix and `{env}` segment.
*   **Action:** Needs update to match S3 pathing structure if GCS is kept, or migrate to S3.

## 5. Commands & Revisions
*   **Status:** **MISSING**.
*   **Gap:** No command endpoint, no revision tracking, no `bases_rev`/`head_rev` logic found in scanned files.

## Summary of Gaps
1.  **Isolation:** Thread/Canvas ownership checks are missing or TODOs.
2.  **Schema:** Relying on legacy `Message` string payloads.
3.  **Commands:** Completely missing.
4.  **Media V2:** Pathing inconsistent with spec.
5.  **Graft:** No gesture capture/replay infrastructure found.
