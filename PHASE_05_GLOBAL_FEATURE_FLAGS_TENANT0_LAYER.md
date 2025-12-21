# PHASE_05_GLOBAL_FEATURE_FLAGS_TENANT0_LAYER

## Goal
Introduce a persistent feature-flag layer that supports tenant-0/global defaults plus per-tenant overrides, ensures flags are authenticated/tenant-scoped, and documents which toggles gate streaming (ws/sse) or control-plane behavior.

## In-scope / Out-of-scope
- **In-scope:** `engines/feature_flags/models.py`, `engines/feature_flags/repository.py`, `engines/feature_flags/service.py`, `engines/feature_flags/routes.py`, `engines/feature_flags/tests/*`, any new `engines/feature_flags/global_repository.py` (if created).
- **Out-of-scope:** Feature flags in other engines, FE flag panels, muscle-namespace toggles.

## Required invariants
1. Feature flags are stored per `(tenant_id, env)` with fallback to a tenant-0 (control plane) bucket when tenant-specific flags absent.
2. Only `owner`/`admin` roles can mutate flags; `member`/`viewer` can read but not write.
3. Global toggles (tenant-0) must explicitly declare whether they apply to WS/SSE, streaming telemetry, or infrastructure gating.
4. Flags persist to Firestore (or other durable backend) instead of in-memory map.

## Allowed modules to change
- `engines/feature_flags/models.py`
- `engines/feature_flags/repository.py`
- `engines/feature_flags/service.py`
- `engines/feature_flags/routes.py`
- `engines/feature_flags/tests/*`
- `engines/identity/routes_analytics.py` (only if referencing new tenant-0 gating values)

## Step-by-step tasks
1. Expand `FeatureFlagRepository` to support Firestore persistence and a `get_global_flags(env)` helper; fallback to `tenant-0` entries when tenant flags absent.
2. Adjust `update_feature_flags` to write both tenant-specific and tenant-0/global toggles (guarded by a new `env`/`tenant_id` whitelist) while maintaining the existing in-memory store for dev mode.
3. Update `routes.py` so `GET /feature-flags` reads tenant-specific flags with fallback to tenant-0; `PUT` remains owner/admin only and records the `tenant_id` from context.
4. Add tests verifying global fallback logic, persistence to Firestore (mocked) and that tenant-level writes do not mutate tenant-0 defaults.
5. Document new tenant-0 global toggles (e.g., `ws_enabled`, `sse_enabled`, `replay_mode`) in repo README or `docs` to inform control-plane teams.

## Tests
- `pytest engines/feature_flags/tests/test_flags.py::test_global_flag_fallback`
- `pytest engines/feature_flags/tests/test_flags.py::test_owner_can_update_flags`
- `pytest engines/feature_flags/tests/test_flags.py::test_firestore_repository_persists`

## Acceptance criteria
- Feature flags persist in Firestore (or dev fallback) and support tenant-0 defaults applied when tenant-specific record missing.
- Only owner/admin roles can write; member/viewer requests receive 403.
- Tests cover fallback/override behavior plus persistence semantics.

## Stop conditions
- Stop if Firestore client setup would require touching runtime_config beyond allowed modules or if Firestore credentials are not available in the environment.
- Stop if global flag defaults require schema changes in other subsystems (document and revisit then).

## Do-not-touch list
- `engines/bossman/routes.py`
- `engines/nexus/*` (not needed for flag persistence).

## Mini execution guardrails
- If any change would modify files outside the allowed list, STOP and raise an issue before editing.
