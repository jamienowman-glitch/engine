# PHASE 1 — Raw Storage (S3) + Tenancy + Lineage

> [!NOTE]
> **DONE**: Implemented `RawStorageService`, `S3RawStorageRepository`, and routes. Verified tenancy, presigned URL generation, and event logging.

Goal:
- Tenant-scoped, immutable raw asset storage in S3 with lineage metadata and presigned upload/register flow.

In-scope (engines only):
- Define `RawAsset` model (asset_id, tenant_id, env, uri, sha256, size_bytes, content_type, captured_at, imported_at, capture_location?).
- `RawStorageRepository` interface + `S3RawStorageRepository` implementing tenant/env-scoped keys `tenants/<tenant_id>/<env>/raw/<asset_id>/<filename>`.
- Routes: `POST /nexus/raw/presign-upload`, `POST /nexus/raw/register`, `GET /nexus/raw/{asset_id}` (metadata-only); JWT + tenant membership; owner/admin for write.
- Lineage metadata captured and logged via DatasetEvents with tenant/env/user/trace and pii_flags/train_ok.
- Config validation for bucket, region, credentials; fail closed when missing.

Out-of-scope:
- Embeddings, LLM calls, behavior/orchestration logic.
- Non-S3 providers beyond contract; no raw → atom transformations here.

Affected engine modules:
- `engines/nexus/raw_storage` (new), `engines/storage` helpers, `engines/identity/auth`, `engines/logging/events`, `engines/config/runtime_config`.

Runtime guarantees added:
- Raw asset writes/read metadata require tenant/env/auth; keys and metadata carry tenant/env.
- Presign/register emits DatasetEvents with lineage refs; no data written if tenant/env missing.
- No raw content stored in Nexus/Firestore; only metadata + S3 URI.

What coding agents will implement later:
- Build models/repos/routes with tenancy enforcement and config validators; mock S3 tests for paths/presign; isolation tests blocking cross-tenant access.
- Logging hooks emitting DatasetEvents for uploads/registrations.

How we know it’s production-ready:
- Tests pass for path construction, presign shape, tenant/env enforcement; wrong-tenant access blocked.
- Upload via presign + register works end-to-end with recorded metadata; errors surface when config missing.
