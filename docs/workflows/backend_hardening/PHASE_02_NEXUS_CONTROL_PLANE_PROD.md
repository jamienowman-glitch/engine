# PHASE_02_NEXUS_CONTROL_PLANE_PROD

## Goal
Enforce RequestContext + AuthContext/membership on Nexus control-plane routes (raw_storage, atoms, packs, cards, search, settings, runs, memory) with assert_context_matches on payload tenant/env, so only authenticated tenants can mutate or read control-plane data.

## Scope lock (allowed to change)
- `engines/nexus/raw_storage/routes.py`
- `engines/nexus/atoms/routes.py`
- `engines/nexus/packs/routes.py`
- `engines/nexus/cards/routes.py`
- `engines/nexus/index/routes.py`
- `engines/nexus/settings/routes.py`
- `engines/nexus/runs/routes.py`
- `engines/nexus/memory/routes.py`
- Tests under `engines/nexus/*/tests`
- DO NOT TOUCH: media/media_v2, chat transports, muscle/video/audio routes.

## Invariants
- Every listed route uses `Depends(get_request_context)` and `Depends(get_auth_context)` with `require_tenant_membership`.
- `assert_context_matches` runs for any payload/query tenant/env.
- Existing kill_switch/rate_limit checks remain intact.
- No new defaults to `t_unknown`.

## Implementation checklist
1. Add AuthContext dependency and membership check to each route module listed.
2. Insert `assert_context_matches(ctx, payload.tenant_id, payload.env)` where payload carries tenant/env (register, create, update).
3. Ensure raw_storage presign/register also enforce auth; defer method fix to Phase 3.
4. Update tests in each module to cover: 401 on missing auth, 403 on tenant mismatch, success on valid context.

## Test plan
- `pytest engines/nexus/raw_storage/tests`
- `pytest engines/nexus/atoms/tests`
- `pytest engines/nexus/packs/tests`
- `pytest engines/nexus/cards/tests`
- `pytest engines/nexus/index/tests`
- `pytest engines/nexus/settings/tests`
- `pytest engines/nexus/runs/tests`
- `pytest engines/nexus/memory/tests`
- Tests assert auth requirement, tenant mismatch rejection, happy-path success.

## Worker Guardrails
- Allowed files: `engines/nexus/raw_storage/routes.py`, `engines/nexus/atoms/routes.py`, `engines/nexus/packs/routes.py`, `engines/nexus/cards/routes.py`, `engines/nexus/index/routes.py`, `engines/nexus/settings/routes.py`, `engines/nexus/runs/routes.py`, `engines/nexus/memory/routes.py`, `engines/nexus/*/tests/*`.
- If you need to change outside scope: STOP and report.
- No refactors; no formatting-only changes.
- FE/agents contract: all Nexus routes require `Authorization: Bearer` + RequestContext headers (`X-Tenant-Id`, `X-Env`); payload tenant/env must match; responses unchanged otherwise.

## Smoke Test Gate
- Before/after run: `pytest engines/nexus/raw_storage/tests engines/nexus/atoms/tests engines/nexus/packs/tests engines/nexus/cards/tests engines/nexus/index/tests engines/nexus/settings/tests engines/nexus/runs/tests engines/nexus/memory/tests`
- Pass = all tests green.

## Negative tests required
- Cross-tenant access blocked (403/400 when token tenant ≠ payload/ctx).
- Missing auth/context fails with 401/400 on representative routes (e.g., raw_storage presign, cards create).

## Log + trace assertions
- None added beyond ensuring RequestContext enforced; keep existing logging untouched but ensure no `t_unknown` defaults introduced.

## Acceptance criteria
- All listed routes return 401/403 on missing/mismatched auth/tenant.
- assert_context_matches executed on payload-bearing endpoints.
- Existing kill_switch/rate_limit behavior preserved.
- All tests above pass.

## Stop conditions
- If any route requires modifying services beyond scope (e.g., Firestore clients), stop and escalate.
- If adding auth breaks mounting in `server.py`, halt and raise.

## Rollback notes
- Revert modified route modules and tests; restore prior dependencies.

## PR slicing
- Single PR covering all Nexus route auth additions + tests.

Safe to hand to worker: YES (clear scope, no new contracts).
