# PHASE_05_GATECHAIN_EXTERNAL_MUTATIONS_PROD

## Goal
Introduce a GateChain helper that enforces KillSwitch → Firearms → StrategyLock/ThreeWise → Budget/KPI/Temperature → Audit on external mutation endpoints, and apply it to the minimum critical routes (raw_storage register, Nexus cards/settings/runs/memory, maybes mutations, analytics_events writes).

## Scope lock (allowed to change)
- `engines/nexus/hardening/gate_chain.py` (new)
- `engines/maybes/service.py`
- `engines/analytics_events/service.py`
- `engines/nexus/raw_storage/routes.py` (hook GateChain)
- `engines/nexus/cards/routes.py`
- `engines/nexus/settings/routes.py`
- `engines/nexus/runs/routes.py`
- `engines/nexus/memory/routes.py`
- Tests under `engines/nexus/hardening/tests`
- DO NOT TOUCH: muscle engines, media_v2, chat transports.

## Invariants
- GateChain executes in order: KillSwitch → Firearms (dangerous actions) → StrategyLock (ThreeWise if required) → Budget/KPI/Temperature → Audit emit.
- Internal draft actions can skip KPI/Temperature only if flagged; still emit audit.
- All hooked routes still honor RequestContext/Auth from prior phases.

## Implementation checklist
1. Create `gate_chain.py` with GateChain class performing ordered checks using existing services (`get_kill_switch_service`, `get_firearms_service`, `get_strategy_lock_service`, `get_budget_service`, `get_kpi_service`, `get_temperature_service`) and emitting audit on success.
2. Define action codes per endpoint (e.g., `raw_asset_register`, `card_create`, `settings_read/write`, `runs_read`, `memory_write`, `maybe_mutation`, `analytics_event_write`).
3. Wrap external mutation routes listed with GateChain.run before service calls; allow skip_metrics flag only for internal drafts if applicable.
4. Add tests in `engines/nexus/hardening/tests` to cover blocks: kill_switch disabled action, firearms missing licence, strategy_lock required, temperature breach.

## Test plan
- `pytest engines/nexus/hardening/tests`
- Targeted route tests where added (e.g., cards/raw_storage) if updated.
- Tests assert correct error codes/order when gates block.

## Worker Guardrails
- Allowed files: `engines/nexus/hardening/gate_chain.py`, `engines/maybes/service.py`, `engines/analytics_events/service.py`, `engines/nexus/raw_storage/routes.py`, `engines/nexus/cards/routes.py`, `engines/nexus/settings/routes.py`, `engines/nexus/runs/routes.py`, `engines/nexus/memory/routes.py`, `engines/nexus/hardening/tests/*`.
- If you need to change outside scope: STOP and report.
- No refactors; no formatting-only changes.
- FE/agents contract: external mutation endpoints now blocked unless gates pass; expect 4xx with error code when blocked; RequestContext/Auth still required from prior phases.

## Smoke Test Gate
- Before/after run: `pytest engines/nexus/hardening/tests`
- Pass = tests green; failures → stop.

## Negative tests required
- GateChain blocks cross-tenant or unauth mutations (ensure 401/403 when Auth missing).
- GateChain blocks when KillSwitch/Firearms/StrategyLock/Temperature rules fail.

## Log + trace assertions
- GateChain should emit audit with `trace_id`/`request_id` from RequestContext on allowed mutations; ensure test checks audit payload contains these identifiers when enabled.

## Acceptance criteria
- GateChain present and reusable; order enforced.
- Listed mutation endpoints call GateChain; return 4xx with descriptive error on block.
- Tests pass.

## Stop conditions
- If GateChain requires modifying services beyond allowed scope, stop.
- If temperature/budget data unavailable causing noisy failures, halt and flag for design input.

## Rollback notes
- Revert new gate_chain module and route hooks; restore prior behavior.

## PR slicing
- Single PR introducing GateChain + applying to listed endpoints + tests.

Safe to hand to worker: YES (clear order, bounded files, existing services reused).
