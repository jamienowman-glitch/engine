# PHASE_03_RAW_STORAGE_PRESIGN_REGISTER_FIX

## Goal
Fix the raw storage presign/register API so it uses the correct service method (`create_presigned_post` or `presign_upload`) while ensuring S3 keys always follow `tenants/{tenant_id}/{env}/...` and the route emits audit/log events before returning.

## In-scope / Out-of-scope
- **In-scope:** `engines/nexus/raw_storage/routes.py`, `engines/nexus/raw_storage/service.py`, `engines/nexus/raw_storage/repository.py`, `engines/logging/event_log.py`, `engines/logging/audit.py`, `engines/nexus/raw_storage/tests/*`.
- **Out-of-scope:** media_v2 storage adapters, FE upload widget code.

## Required invariants
1. `S3RawStorageRepository._get_key` always returns a key prefixed with `tenants/{tenant_id}/{env}/raw/...` and is used by both presign and register flows.
2. Routes call the actual service helper (either rename to `create_presigned_post` or adjust route wiring) instead of the missing method invoked today.
3. Audit/log events emitted during presign and register include `event_type`, `asset_id`, and the `request_id` from the enclosing `RequestContext`.
4. Presign/register both require `RequestContext` + `AuthContext` gating from previous phases.

## Allowed modules to change
- `engines/nexus/raw_storage/routes.py`
- `engines/nexus/raw_storage/service.py`
- `engines/nexus/raw_storage/repository.py`
- `engines/nexus/raw_storage/tests/*`
- `engines/logging/event_log.py`
- `engines/logging/audit.py`

## Step-by-step tasks
1. Rename/add method on `RawStorageService` so `presign_upload` exposes a clearly named `create_presigned_post` (or vice versa) and update every caller (route + tests) to use the correct name; ensure the service still emits `EventLogEntry` with `event_type`/`asset_type`.
2. Revisit `S3RawStorageRepository._get_key` to assert tenant/env numeric values before building the key string; add unit test ensuring invalid tenant IDs raise `HTTPException`.
3. Make sure `register_asset` builds URIs via `get_uri` that reference the same key prefix and record `metadata` as required; `RequestContext` injection ensures tenant/env align.
4. Update `engines/logging/event_log.py` default logger to include `trace_id`/`request_id` metadata (if not already present) and ensure it writes to the Nexus backend with tenant-bound collection.
5. Add/update tests in `engines/nexus/raw_storage/tests` to cover the renamed method, `RequestContext` gating, key prefix enforcement, and success of audit/log path.

## Tests
- `pytest engines/nexus/raw_storage/tests/test_raw_storage.py::test_presign_key_prefix`
- `pytest engines/nexus/raw_storage/tests/test_raw_storage.py::test_register_emits_event`
- `pytest engines/logging/events/tests/test_logging_engine.py::test_event_has_trace_id`

## Acceptance criteria
- Running the presign endpoint calls the correct service helper and returns S3 fields for `tenants/{tenant}/{env}/raw/...` keys.
- Registering an asset builds URIs via the same key helper and emits an audit/log dataset event referencing the request trace.
- Tests verify gating, key prefix enforcement, and logging outputs contain `trace_id`/`request_id`.

## Stop conditions
- Stop if adjusting the service requires touching storage backends outside S3 (e.g., GCS) until a scoped follow-up is approved.
- Stop if the audit logger change would require runtime_config modifications outside allowed modules.

## Do-not-touch list
- `engines/media_v2/routes.py`
- `engines/nexus/packs/routes.py` (unless already in allowed phases).

## Mini execution guardrails
- If any file outside the allowed modules must change, STOP and report before editing.
