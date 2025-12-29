# PHASE 2 — Maybes Persistence + Safety Metadata

DO NOT TOUCH:
- Strategy Lock, Firearms, Tenant/Auth shapes, Temperature/KPI semantics.
- 3D/video/audio engines.
- No new env vars; no prompts/agent logic in engines.

Allowed paths:
- engines/maybes/* (routes/service/repo/models/tests)
- engines/identity/auth.py (for membership checks)
- engines/logging/events.py, engines/dataset/events/schemas.py (for DatasetEvents/flags)
- engines/config/runtime_config.py (read-only for config names)

Tests to run:
- `python -m pytest engines/maybes/tests`
- `python -m pytest engines/dataset/events/tests` (if affected by flags)

Goal:
- Make Maybes reliable with tenant/user/env scoping and safety metadata (pii_flags/train_ok) using Firestore backend by default.

Plan tasks:
- Ensure Maybes writes/read metadata include tenant_id/env and optional user_id; enforce membership on writes.
- Add/verify PII flags attachment (flag only, do not redact content) and train_ok propagation per preferences.
- Ensure persistence is restart-safe with Firestore backend as default; validate config names are canonical.
- Update/extend tests for create/list/filter by tenant/user/env and safety flags; no changes to Strategy Lock/Firearms/Auth semantics.

Success criteria:
- Maybes persists and survives restart; create/list/filter are tenant/user/env scoped.
- Tests for tenant isolation and safety metadata pass; no non-Maybes engines modified.

Failure modes + rollback:
- If Firestore config missing, fail closed with clear error; document as known failure.
- If existing tests in non-Maybes areas fail, mark known failure; do not alter core behavior.

Agent prompt (run after reading above):
```
You are a coding agent.
Scope: PHASE 2 — Maybes Persistence + Safety Metadata (docs/workflows/88mph/PHASE_02_MAYBES_PERSISTENCE.md).
Tasks: harden Maybes persistence (tenant/env/user scoping, pii_flags/train_ok), ensure Firestore default, add tests for isolation and metadata. Do not touch Strategy Lock/Firearms/Auth/KPI/Temperature or 3D/video/audio. Reuse canonical env vars only.
Tests: python -m pytest engines/maybes/tests [and related DatasetEvent tests if touched].
Stop when persistence and tests are in place.
```
