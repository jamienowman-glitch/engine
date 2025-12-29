# PHASE_06_STORAGE_PREFIX_ENFORCEMENT_PROD

## Goal
Guarantee all binary storage uses tenant/env-prefixed keys and rejects unscoped writes: enforce prefix checks in media_v2 and canvas artifacts, and add assertions so prod cannot fall back to local tmp paths for tenant data.

## Scope lock (allowed to change)
- `engines/media_v2/service.py`
- `engines/media_v2/models.py` (if needed for validation)
- `engines/canvas_artifacts/service.py`
- `engines/canvas_artifacts/router.py` (only to assert tenant/env)
- Tests under `engines/media_v2/tests`, `engines/canvas_artifacts/tests`
- DO NOT TOUCH: raw_storage (handled earlier), muscle media routes.

## Invariants
- All generated keys include `tenants/{tenant_id}/{env}/...` prefix.
- Requests must carry RequestContext; assert_context_matches aligns payload tenant/env.
- Prod paths do not silently fall back to local temp; local fallback allowed only in explicit dev/test branch.

## Implementation checklist
1. In media_v2 service, ensure key builders prepend `tenants/{ctx.tenant_id}/{ctx.env}/...`; add validation to reject missing tenant/env.
2. In canvas_artifacts service/router, assert payload canvas writes use tenant/env from RequestContext and enforce prefix on stored artifacts (reuse media_v2 helper if available).
3. Add tests to assert key prefix enforcement, rejection of missing tenant/env, and that prod mode does not use local fallback.

## Test plan
- `pytest engines/media_v2/tests/test_media_v2_endpoints.py`
- `pytest engines/canvas_artifacts/tests/test_artifacts.py`
- Tests assert key prefixes and auth/context requirements; prod mode avoids local temp.

## Worker Guardrails
- Allowed files: `engines/media_v2/service.py`, `engines/media_v2/models.py` (if needed), `engines/canvas_artifacts/service.py`, `engines/canvas_artifacts/router.py`, `engines/media_v2/tests/*`, `engines/canvas_artifacts/tests/*`.
- If you need to change outside scope: STOP and report.
- No refactors; no formatting-only changes.
- FE/agents contract: uploads/registrations must carry RequestContext headers; stored keys must be `tenants/{tenant_id}/{env}/...`; prod must not fall back to local temp paths.

## Smoke Test Gate
- Before/after run: `pytest engines/media_v2/tests/test_media_v2_endpoints.py engines/canvas_artifacts/tests/test_artifacts.py`
- Pass = tests green.

## Negative tests required
- Cross-tenant attempt (payload vs RequestContext) rejected.
- Missing tenant/env or auth fails fast on upload/register.

## Log + trace assertions
- Not adding new logs; ensure any emitted events keep tenant/env from RequestContext; reject `t_unknown`; key-building functions must assert tenant/env present.

## Acceptance criteria
- media_v2 and canvas artifacts always write to tenant/env-prefixed paths.
- Attempts without tenant/env fail fast.
- Tests pass.

## Stop conditions
- If enforcing prefixes requires altering storage backends beyond scope, stop.
- If artifacts rely on other modules not listed, halt and escalate.

## Rollback notes
- Revert media_v2/canvas_artifacts changes and tests.

## PR slicing
- Single PR for storage prefix enforcement + tests.

Safe to hand to worker: YES (narrow files; explicit validations).
