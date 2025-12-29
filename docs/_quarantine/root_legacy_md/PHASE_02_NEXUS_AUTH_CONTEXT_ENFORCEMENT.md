# PHASE_02_NEXUS_AUTH_CONTEXT_ENFORCEMENT

## Goal
Enforce `RequestContext` + `get_auth_context` (tenant membership/role) on all Nexus write/read routes that surfaced in the Coverage Map (raw_storage, atoms, packs, cards, index/search, settings, runs, memory) so no control-plane endpoint can be called without an explicit tenant+auth assertion.

## In-scope / Out-of-scope
- **In-scope:** `engines/nexus/raw_storage/routes.py`, `engines/nexus/atoms/routes.py`, `engines/nexus/packs/routes.py`, `engines/nexus/cards/routes.py`, `engines/nexus/index/routes.py`, `engines/nexus/settings/routes.py`, `engines/nexus/runs/routes.py`, `engines/nexus/memory/routes.py`, `engines/nexus/atoms/service.py` (if gating logic added), supporting tests under `engines/nexus/*/tests`, `engines/kill_switch/service.py`, `engines/nexus/hardening/rate_limit.py` (only to keep gating consistent).
- **Out-of-scope:** Media routes, FE, chat HTTP endpoints.

## Required invariants
1. Every route must declare `RequestContext = Depends(get_request_context)` and `auth=Depends(get_auth_context)`; `require_tenant_membership(auth, ctx.tenant_id)` before calling service.
2. `assert_context_matches` must validate any tenant/env fields provided in payload/query before handing to service.
3. Kill switch/rate-limit gating and Audit emission (from previous phases) should wrap writes at controller level when present.
4. No new `t_unknown` fallbacks in production mode; tests must cover error path for missing context.

## Allowed modules to change
- `engines/nexus/raw_storage/routes.py`
- `engines/nexus/atoms/routes.py`
- `engines/nexus/packs/routes.py`
- `engines/nexus/cards/routes.py`
- `engines/nexus/index/routes.py`
- `engines/nexus/settings/routes.py`
- `engines/nexus/runs/routes.py`
- `engines/nexus/memory/routes.py`
- `engines/nexus/raw_storage/tests/*`, `engines/nexus/atoms/tests/*`, `engines/nexus/cards/tests/*`, `engines/nexus/settings/tests/*`, `engines/nexus/runs/tests/*`, `engines/nexus/memory/tests/*`
- `engines/kill_switch/service.py` (only to ensure gating helper interface remains compatible).

## Step-by-step tasks
1. Add a shared helper in `engines/nexus/hardening` (e.g., `enforce_tenant_context(ctx, auth)`) that runs membership and optional role checks; reuse this helper across all Nexus route files.
2. Update each Nexus route file listed above to declare the dependencies, call the helper, and assert payload tenant/env alignment via `assert_context_matches` before invoking services.
3. For read-only routes (e.g., settings/memory list), restrict to `require_tenant_membership`; for write operations (cards/create, raw/register, memory session writes) also require hit of kill switch/rate limit (already present) before service call.
4. Add pytest coverage to each module's `tests` directory verifying: missing auth returns 401, tenant mismatch returns 403/404, proper context allows access (mocking or requesting with valid context). New tests should focus on `cards/routes.py` and `raw_storage/routes.py` as representative.
5. Document the new requirement in `docs/workflows/*` (if referenced) or inline comment to remind maintainers that every Nexus route is guarded.

## Tests
- `pytest engines/nexus/cards/tests/test_cards.py::test_create_requires_auth`
- `pytest engines/nexus/raw_storage/tests/test_raw_storage.py::test_presign_requires_tenant_context`
- `pytest engines/nexus/settings/tests/test_settings.py::test_get_apps_requires_auth`

## Acceptance criteria
- Any call to the listed Nexus endpoints without Authorization or tenant headers returns 401.
- Tenant mismatch (auth token tenant vs query/payload tenant) results in 403/400 before service logic runs.
- Gated operations still pass kill switch/rate limit checks with valid context.

## Stop conditions
- Halt if any Nexus route requires touching modules outside the allowed list (e.g., new services) or if gating logic needs cross-cutting changes beyond route files.
- Pause if tests expose missing repository stubs that require Firestore clients beyond simple mocks; escalate for infra support.

## Do-not-touch list
- `engines/nexus/vector_explorer/*` (handled elsewhere).
- `engines/media_v2/*` (muscle scope out).

## Mini execution guardrails
- If any allowed file change would cascade to modules outside this list, STOP and report before editing.
