# PHASE_07_PRIVACY_TRAIN_PREFS_API_PERSISTENCE

## Goal
Expose authenticated APIs to set per-tenant and per-user training opt-out preferences, persist them (Firestore-backed once enabled), and ensure logging/audit honors stored preferences when computing `train_ok`.

## In-scope / Out-of-scope
- **In-scope:** `engines/privacy/train_prefs.py`, new router `engines/privacy/routes.py`, tests under `engines/privacy/tests/*`, updates to `engines/logging/events/engine.py` (if needed to call the persistent repo), and documentation in `docs/workflows` referencing training opt-outs.
- **Out-of-scope:** UI opt-out forms, FE telemetry.

## Required invariants
1. APIs require `RequestContext` + `AuthContext`; only members can set tenant-wide opts, user opts require matching user IDs.
2. Repository defaults to in-memory but should support Firestore when `PRIVACY_BACKEND=firestore` is set via `train_prefs` helper.
3. Logging engine uses `get_training_pref_service()` so the persisted prefs influence `train_ok`; no new in-memory-only copies are created per request.
4. Prefer tenants `t_system`/`t_northstar` for tenant-0 default opt-out toggles.

## Allowed modules to change
- `engines/privacy/train_prefs.py`
- `engines/privacy/routes.py` (new file)
- `engines/privacy/tests/*`
- `engines/logging/events/engine.py` (to ensure persistent service used)
- `engines/common/identity.py` (only if helper needed for verifying `user_id` in context)

## Step-by-step tasks
1. Extend `TrainingPreferenceService` to support Firestore (or other durable backend) via a new repository implementation, controlled by `PRIVACY_BACKEND` env var; expose `set_user_opt_out`, `set_tenant_opt_out`, and `train_ok` as before.
2. Create `engines/privacy/routes.py` with routes like `POST /privacy/train-prefs/tenant`, `POST /privacy/train-prefs/user`, `GET /privacy/train-prefs` that enforce auth/membership and validate tenant/user IDs.
3. Ensure `train_prefs` module exposes a setter for the service (for tests) and the logging engine uses the same singleton, so persistence is shared.
4. Add integration tests under `engines/privacy/tests` covering tenant/user opt-out flows, verifying only owners/admins can set tenant opts and that user opts respect the JWT `user_id`.
5. Update docs to mention the persistence guarantees and how training opt-out integrates with audit logging.

## Tests
- `pytest engines/privacy/tests/test_train_prefs.py::test_tenant_opt_out_requires_admin`
- `pytest engines/privacy/tests/test_train_prefs.py::test_user_opt_out_validated`
- `pytest engines/privacy/tests/test_train_prefs.py::test_logging_respects_prefs`

## Acceptance criteria
- APIs exist to set/get tenant/user training preferences with enforced auth and correct `RequestContext` alignment.
- Persisted preferences are used by the logging engine so `train_ok` respects user/tenant opt-outs.
- Firestore backend is optional but available when `PRIVACY_BACKEND=firestore`; fallback to in-memory occurs gracefully.

## Stop conditions
- Stop if persistence requires touching infrastructure modules beyond allowed (e.g., new secret managers) without coordination.
- Stop if doc updates would require altering FE contractual references (document and escalate).

## Do-not-touch list
- `engines/logging/audit.py`
- `engines/identity/routes_*` (unless integration needed and approved).

## Mini execution guardrails
- If a required change touches modules outside the allowed list, STOP and report before continuing.
