# PHASE_03_RAW_STORAGE_PRESIGN_REGISTER_PROD

## Goal
Fix raw storage API surface: align route call with existing service method (presign helper), enforce AuthContext + tenant/env checks, and ensure S3 key/URI remain `tenants/{tenant_id}/{env}/raw/...` while emitting audit/event logs.

## Scope lock (allowed to change)
- `engines/nexus/raw_storage/routes.py`
- `engines/nexus/raw_storage/service.py`
- `engines/nexus/raw_storage/repository.py`
- `engines/logging/event_log.py` (only to include trace/request metadata)
- `engines/logging/audit.py` (only to ensure audit emit uses real logger)
- Tests under `engines/nexus/raw_storage/tests`
- DO NOT TOUCH: media_v2, other Nexus modules, chat transports.

## Invariants
- Routes require RequestContext + AuthContext; assert_context_matches on asset payloads.
- Presign uses the actual service method name (no missing `create_presigned_post` call).
- S3 keys always `tenants/{tenant_id}/{env}/raw/{asset_id}/{filename}`; register builds URI from same helper.
- Audit/event logging does not swallow errors silently.

## Implementation checklist
1. Rename or add service method so routes call the real presign helper (align `presign_upload` → service method name).
2. Add AuthContext + membership to routes; keep assert_context_matches on register.
3. In repository `_get_key`, enforce prefix format; raise HTTP 400/500 on missing bucket.
4. Ensure `register_asset` uses repo.get_uri; log EventLogEntry with request_id/trace if available.
5. Update tests to cover: auth required, key prefix correctness, register emits event, missing bucket error.

## Test plan
- `pytest engines/nexus/raw_storage/tests`
- Tests assert auth/membership, key prefix, presign route calls real method, register emits event.

## Worker Guardrails
- Allowed files: `engines/nexus/raw_storage/routes.py`, `engines/nexus/raw_storage/service.py`, `engines/nexus/raw_storage/repository.py`, `engines/logging/event_log.py`, `engines/logging/audit.py`, `engines/nexus/raw_storage/tests/*`.
- If you need to change outside scope: STOP and report.
- No refactors; no formatting-only changes.
- FE/agents contract: must send RequestContext headers (`X-Tenant-Id`, `X-Env`, optional `X-User-Id`) + `Authorization`; presign returns S3 POST fields with key `tenants/{tenant}/{env}/raw/...`; register requires same tenant/env and logs event.

## Smoke Test Gate
- Before/after run: `pytest engines/nexus/raw_storage/tests`
- Pass = all tests green; failure → stop.

## Negative tests required
- Auth missing → 401/403 on presign/register.
- Cross-tenant mismatch (payload vs RequestContext) rejected.

## Log + trace assertions
- EventLog/audit emit should include `request_id`/`trace_id` if available; ensure test checks presence or non-empty metadata; no `t_unknown` tenants.

## Acceptance criteria
- Presign/register routes succeed with auth; 401/403 on missing.
- Key prefix fixed; URIs align with repo.
- Audit/event logging executed without silent drop.
- Tests pass.

## Stop conditions
- If changes require touching storage backends beyond S3 scope, stop.
- If audit/log changes cascade outside allowed files, halt and escalate.

## Rollback notes
- Revert modified files; ensure presign route restored to prior behavior if needed.

## PR slicing
- Single PR for raw storage fixes + tests.

Safe to hand to worker: YES (bounded files; clear tests).
