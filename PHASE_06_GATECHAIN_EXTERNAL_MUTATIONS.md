# PHASE_06_GATECHAIN_EXTERNAL_MUTATIONS

## Goal
Guarantee every external mutation (Nexus writes, raw storage changes, memory writes, analytics events) runs the ordered gate chain: KillSwitch → Firearms → StrategyLock/ThreeWise → Budget/KPI/Temperature → Audit emit.

## In-scope / Out-of-scope
- **In-scope:** `engines/nexus/hardening` (new module `gate_chain.py`), routes for external mutations (`engines/nexus/cards/routes.py`, `engines/nexus/raw_storage/routes.py`, `engines/nexus/memory/routes.py`, `engines/nexus/settings/routes.py`, `engines/nexus/index/routes.py`, `engines/nexus/runs/routes.py`, `engines/maybes/service.py`, `engines/analytics_events/service.py` if applicable), gate services (`engines/kill_switch/service.py`, `firearms/service.py`, `strategy_lock/service.py`, `budget/service.py`, `kpi/service.py`, `temperature/service.py`), plus tests touching these modules.
- **Out-of-scope:** Pure read routes (those already gated in Phase 2) and muscle engine mutations.

## Required invariants
1. GateChain helper must execute services in the mandated order and raise HTTPException with tagged error code if any step blocks.
2. Controller code for external mutations must call the helper before issuing writes or presigned URLs.
3. StrategyLock checks must request `three_wise` verdict via `require_strategy_lock_or_raise`; carve out internal canvas edits that bypass later gates but still emit audit events with `persist=false`.
4. Budget/KPI/Temperature gates must validate surface-level thresholds before allowing mutation; if metrics not present, fail safe (deny or require manual override).

## Allowed modules to change
- `engines/nexus/hardening/gate_chain.py` (new module)
- `engines/nexus/cards/routes.py`
- `engines/nexus/raw_storage/routes.py`
- `engines/nexus/memory/routes.py`
- `engines/nexus/settings/routes.py`
- `engines/nexus/index/routes.py`
- `engines/nexus/runs/routes.py`
- `engines/maybes/service.py`
- `engines/analytics_events/service.py`
- `engines/kill_switch/service.py`
- `engines/firearms/service.py`
- `engines/strategy_lock/service.py`
- `engines/budget/service.py`
- `engines/kpi/service.py`
- `engines/temperature/service.py`
- `engines/nexus/hardening/tests/*`

## Step-by-step tasks
1. Create `GateChain` class in `engines/nexus/hardening/gate_chain.py` that accepts `RequestContext`, `AuthContext` (if needed), action/subject metadata, and sequentially calls `kill_switch.ensure_action_allowed`, `firearms.require_licence_or_raise` (when action in `DANGEROUS_ACTIONS`), `strategy_lock.require_strategy_lock_or_raise`, and `budget.summary`/`kpi`/`temperature` gating helpers; include config to skip KPI/Temperature for internal drafts.
2. Update external mutation routes/services to invoke `GateChain.run(action, surface, subject_type, subject_id)` before performing mutations; reuse the same helper in raw storage register, card creation, memory writes, and analytics event writes (if they mutate external state). Document the action codes (e.g., `card_create`, `metadata_update`).
3. Update `StrategyLockService` (if necessary) to expose `check_action_allowed` outputs used by `GateChain` when building errors with lock IDs and three-wise verdict info.
4. Add pytest coverage under `engines/nexus/hardening/tests` verifying gate chain blocks when `KillSwitch` disables an action, when `Firearms` denies, when `StrategyLock` denies, and when `Temperature` corridor is breached.
5. For internal canvas drafts that skip KPI/Temperature, add a flag in the helper (e.g., `skip_metrics=True`) and ensure audit events still emit with `persist=false`; tests should document this bypass.

## Tests
- `pytest engines/nexus/hardening/tests/test_gate_chain.py::test_kill_switch_blocks`
- `pytest engines/nexus/hardening/tests/test_gate_chain.py::test_strategy_lock_requires_three_wise`
- `pytest engines/nexus/hardening/tests/test_gate_chain.py::test_temperature_breach_blocks`

## Acceptance criteria
- Every external mutation request hits `GateChain` and returns 403/409 with structured error code on the first failing control.
- GateChain can skip KPI/Temperature for known internal drafts while still auditing the intent.
- Tests cover all major gate failures.

## Stop conditions
- Halt if GateChain introduces circular dependencies among services (e.g., budget needing audit events that themselves call GateChain); escalate and refactor.
- Stop if supporting tests require touching non-allowed modules (e.g., global runtime config) before finishing.

## Do-not-touch list
- `engines/media_v2/*`
- `engines/video_*/*`

## Mini execution guardrails
- If implementing GateChain requires modifying files outside the allowed modules, STOP and raise the issue before proceeding.
