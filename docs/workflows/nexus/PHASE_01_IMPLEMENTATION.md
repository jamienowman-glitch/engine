# PHASE 1 IMPLEMENTATION PLAN

## Summary
Implement tenant-scoped raw asset storage logic backed by S3 (via `boto3`). This includes the `RawAsset` Pydantic model, a `RawStorageRepository` interface with an S3 implementation, and a Service layer to handle presigned URL generation and asset registration. New API routes `POST /nexus/raw/presign-upload` and `POST /nexus/raw/register` will be exposed and mounted in the main chat application.

## User Review Required
> [!IMPORTANT]
> **Tenancy & Keys**: This implementation strictly enforces tenancy. It expects `RAW_BUCKET` env var to be set. For S3 access, it relies on standard `boto3` chain (IAM role or env vars). Ensure the runtime environment has write access to the target bucket.

## Proposed Changes

### `engines/nexus`
#### [NEW] [models.py](file:///Users/jaynowman/dev/northstar-engines/engines/nexus/raw_storage/models.py)
- Define `RawAsset` model:
  - `asset_id`: uuid (generated if not provided)
  - `tenant_id`: str (enforced)
  - `env`: str
  - `uri`: str (s3://...)
  - `sha256`: str
  - `size_bytes`: int
  - `content_type`: str
  - `created_at`: datetime
  - `metadata`: dict

#### [NEW] [repository.py](file:///Users/jaynowman/dev/northstar-engines/engines/nexus/raw_storage/repository.py)
- `RawStorageRepository` (Protocol/ABC)
- `S3RawStorageRepository` implementation:
  - `generate_presigned_post(tenant_id, env, filename, content_type)` -> `(url, fields, asset_id)`
  - `register_metadata(asset)` -> `RawAsset`
  - Key structure: `tenants/{tenant_id}/{env}/raw/{asset_id}/{filename}`

#### [NEW] [service.py](file:///Users/jaynowman/dev/northstar-engines/engines/nexus/raw_storage/service.py)
- `RawStorageService`:
  - `presign_upload(ctx, filename, content_type)`
  - `register_asset(ctx, asset_id, filename, metadata...)`
  - Emits `DatasetEvent` for `raw_asset_presigned` and `raw_asset_registered`.

#### [NEW] [routes.py](file:///Users/jaynowman/dev/northstar-engines/engines/nexus/raw_storage/routes.py)
- `presign_upload` (POST)
- `register` (POST)
- `get_asset` (GET, metadata only)
- Dependencies: `get_request_context`

#### [NEW] [__init__.py](file:///Users/jaynowman/dev/northstar-engines/engines/nexus/raw_storage/__init__.py)
- Exports.

### `engines/chat`
#### [MODIFY] [server.py](file:///Users/jaynowman/dev/northstar-engines/engines/chat/service/server.py)
- Mount `engines.nexus.raw_storage.routes.router` to the main app.

## Verification Plan

### Automated Tests
Create `engines/nexus/raw_storage/tests/test_raw_storage.py`:
- **Unit Tests**:
  - Test `S3RawStorageRepository` key generation logic (ensure strict `tenant_id` scoping).
  - Test service logic emits `DatasetEvent` (mocking the event logger).
  - Test Pydantic model validation.
- **Route Tests**:
  - `TestClient` tests for endpoints.
  - Verify 403 if `tenant_id` missing in context.
  - Verify `DatasetEvent` is called.

**Command**:
```bash
pytest engines/nexus/raw_storage/tests/test_raw_storage.py
```

### Manual Verification
1. **Mock S3**: Since we may not have live S3 creds in this env, tests will use `moto` or mocks for `boto3`.
2. **Local Run**:
   - Run: `uvicorn engines.chat.service.server:app`
   - Curl `POST /nexus/raw/presign-upload` with valid headers.
   - Verify 200 OK and JSON response with `url` and `fields`.

### No Prompts Compliance
- Verify no prompts are embedded in `service.py` or `routes.py`.
- Run `grep -r "prompt" engines/nexus/raw_storage` (should be empty).
