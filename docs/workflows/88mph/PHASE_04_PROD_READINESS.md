# PHASE 4 — Production Readiness Pass

DO NOT TOUCH:
- Strategy Lock, Firearms, Tenant/Auth shapes, Temperature/KPI semantics.
- 3D/video/audio engines.
- No new env vars; no prompts/agent logic in engines.

Allowed paths:
- docs/workflows/88mph/* (this lane)
- engines/bossman/routes.py (read-only additions for freshness/health fields)
- engines/logging/events.py, engines/dataset/events/schemas.py (consistency checks)
- engines/budget/* (visibility only), engines/nexus/backends/* (sink indicators)
- docs/infra/* for operator runbook

Tests to run:
- `python -m pytest engines/bossman/tests` (if present)
- `python -m pytest engines/logging/events/tests` (if logging touched)

Goal:
- Ensure multi-tenant onboarding is observable: freshness timestamps, sink backend indicator, and a concise “how to run prod-ish dev” doc.

Plan tasks:
- Add/read Bossman dashboard fields for freshness/health and sink backend indicator (read-only surfaces).
- Verify DatasetEvent pipeline consistency (train_ok, pii_flags) without changing semantics; document any gaps.
- Write a short operator runbook in this lane for “prod-ish dev” (auth, tenant/env headers, sink configs).

Success criteria:
- Bossman dashboard surfaces freshness/health + sink backend info without altering existing behavior.
- Logging pipeline verified; any gaps documented, not altered.
- Operator doc exists and is tenant/env/auth aware.

Failure modes + rollback:
- If Bossman changes risk semantics, revert and document; do not change Strategy Lock/Firearms/Auth/KPI/Temperature.
- If logging tests fail outside scope, document known failure; no semantic changes.

Agent prompt (run after reading above):
```
You are a coding agent.
Scope: PHASE 4 — Production Readiness Pass (docs/workflows/88mph/PHASE_04_PROD_READINESS.md).
Tasks: add/read-only freshness/health and sink indicators to Bossman dashboard; verify logging DatasetEvent consistency; write prod-ish dev runbook in this lane. Do not alter Strategy Lock/Firearms/Auth/KPI/Temperature or 3D/video/audio. Reuse existing env vars only.
Tests: python -m pytest engines/bossman/tests [and logging tests if touched].
Stop when surfaces and docs are updated and tests pass.
```
