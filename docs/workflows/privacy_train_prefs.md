# Privacy Train Preferences

## Overview
Training preference APIs let tenants opt out of telemetry/training on a per-tenant or per-user basis. All routes require the `RequestContext` headers plus a valid bearer token and enforce tenant membership before touching the persisted flags.

## Endpoints
- `POST /privacy/train-prefs/tenant` – owners/admins/members set a tenant-wide opt-out into the current `env`. The request body only needs `{ "opt_out": true|false }` because the tenant/env are derived from the context.
- `POST /privacy/train-prefs/user` – requires the JWT `user_id` to match the provided `user_id` so an individual controls their own opt-out. The tenant and env are still taken from the request context.
- `GET /privacy/train-prefs` – lists the tenant/env prefs (and optionally a single user via `user_id` query) and reports the computed `train_ok` alongside the current values.

## Persistence
The service currently defaults to an in-memory store, but setting `PRIVACY_BACKEND=firestore` causes the repo to write documents into the `training_preferences` collection keyed by `tenant__env__user`. Missing prefs fall back gracefully, so a restart without Firestore still works locally.

## Logging Integration
`engines/logging/events/engine.py` now resolves `get_training_pref_service()` before deciding `train_ok`, ensuring the persisted tenant/user opt-outs influence every audit/telemetry event that flows through the engine.

## Operational Notes
- Tenants `t_system`/`t_northstar` are suggested owners of tenant-zero defaults; their docs should pre-populate Firestore entries if a control-plane opt-out is desired.
- The Firestore backend requires `GCP_PROJECT_ID`/`GCP_PROJECT` and the `google-cloud-firestore` library, but tests and dev builds fall back to memory when the env var is absent.
