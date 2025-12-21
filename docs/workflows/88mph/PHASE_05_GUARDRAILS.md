# PHASE 5 — Guardrail Sweep

DO NOT TOUCH:
- Strategy Lock, Firearms, Tenant/Auth shapes, Temperature/KPI semantics.
- 3D/video/audio engines.
- No new env vars; no prompts/agent logic in engines.

Allowed paths:
- engines/maybes/* (new endpoints only)
- engines/identity/auth.py (auth checks)
- engines/strategy_lock/* (read-only; hook only if needed)
- engines/firearms/* (read-only; hook only if needed)
- docs/infra/AUTH_TENANT_SPINE_DEV_RUN.md, docs/constitution/STRATEGY_LOCK_ACTIONS.md (reference)

Tests to run:
- `python -m pytest engines/maybes/tests`
- `python -m pytest engines/strategy_lock/tests/test_strategy_lock_routes.py` (only if hooks touched)

Goal:
- Ensure newly added Maybes endpoints are correctly gated; document gate matrix.

Plan tasks:
- Confirm membership/role checks on all Maybes write routes.
- If a write route is “strategic config,” add Strategy Lock gate hook (no semantic changes); if dangerous/destructive, add Firearms hook; otherwise document rationale for being ungated.
- Update gate matrix/docs to reflect Maybes endpoints and gating decisions.
- Add tests showing gates succeed/fail appropriately.

Success criteria:
- Tests pass for gating; Maybes routes enforce membership and documented gate status.
- Gate matrix updated; no changes to Strategy Lock/Firearms semantics.

Failure modes + rollback:
- If gating introduces failures, revert hooks and document the gap instead of changing core semantics.

Agent prompt (run after reading above):
```
You are a coding agent.
Scope: PHASE 5 — Guardrail Sweep (docs/workflows/88mph/PHASE_05_GUARDRAILS.md).
Tasks: verify/add membership/role gating on Maybes writes; add Strategy Lock/Firearms hooks only if applicable; update gate matrix; add gating tests. Do not change Strategy Lock/Firearms/Auth/KPI/Temperature semantics or 3D/video/audio. Use existing env vars only.
Tests: python -m pytest engines/maybes/tests [plus strategy_lock tests if hooks touched].
Stop when gating and docs are updated.
```
