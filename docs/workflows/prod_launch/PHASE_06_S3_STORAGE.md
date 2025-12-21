# PHASE 06 — S3 Raw Storage + Signed URLs + Tenant/Env Prefixing

1. Goal
- Provide real S3-backed raw asset storage with tenant/env prefixing and signed upload/download URLs.

2. In scope
- S3 storage adapter with deterministic key format: tenants/<tenant_id>/<env>/raw/<asset_id>/<filename>.
- Routes: presign upload, register asset metadata, fetch metadata, presign download.
- Asset registry metadata including sha256, size_bytes, content_type, captured_at/imported_at, source refs (optional coarse location).

3. Out of scope
- Embeddings/vector/Nexus ingestion.
- New env var names.
- 3D/video/audio processing.

4. Hard boundaries (DO NOT TOUCH)
- Strategy Lock, Firearms, KPI/Temperature semantics.
- 3D/video/audio engines.
- Card/prompt logic.

5. Affected modules
- engines/storage or engines/nexus/raw_storage (adapter), related routes.
- engines/identity/auth for auth checks.
- engines/logging/events for DatasetEvents.
- tests under engines/storage/tests or engines/nexus/raw_storage/tests.

6. API surface / routes
- POST /storage/raw/presign-upload (inputs: filename, content_type, size_bytes) → signed PUT URL + asset_id.
- POST /storage/raw/register (asset_id, sha256, size_bytes, content_type, captured_at/imported_at, source refs).
- GET /storage/raw/{asset_id} (metadata only).
- POST /storage/raw/presign-download (asset_id) → signed GET URL.
- All tenant/env scoped; membership required; owner/admin for writes.

7. Data model changes
- RawAsset: asset_id, tenant_id, env, uri, sha256, size_bytes, content_type, captured_at, imported_at, source_ref?, metadata{}.

8. Security & tenant binding
- require_tenant_membership; enforce tenant/env in keys and metadata; reject cross-tenant access.

9. Safety hooks
- DatasetEvents for presign/register/download with tenant/env/user/trace; no Strategy Lock/Firearms changes unless storage config classified (document if needed).

10. Observability
- Logs/metrics for presign usage, register success/failure; storage health probe optional.

11. Config / env vars
- Reuse canonical S3 envs (e.g., RAW_BUCKET, AWS region/profile if present). Missing bucket/credentials must fail fast.

12. Tests
- Pytests for key construction, presign shapes (mock S3), tenant isolation, register/read metadata, error on missing config.

13. Acceptance criteria
- Can presign upload, upload file, register metadata, retrieve metadata, presign download under tenant/env prefixes; cross-tenant access blocked.

14. Smoke commands
- curl -X POST /storage/raw/presign-upload -H auth/tenant/env -d '{"filename":"a.txt","content_type":"text/plain","size_bytes":10}'
