# LANE A – Codex Mini Execution Prompt

## Scope lock
Allowed files/modules only:
- `engines/chat/service/ws_transport.py`
- `engines/chat/service/sse_transport.py`
- `engines/realtime/isolation.py`
- `engines/chat/service/tests/*`
- `engines/common/identity.py` (only if required for trace_id propagation)
- `engines/nexus/raw_storage/routes.py`
- `engines/nexus/raw_storage/service.py`
- `engines/nexus/raw_storage/repository.py`
- `engines/logging/event_log.py`
- `engines/logging/audit.py`
- `engines/nexus/raw_storage/tests/*`
- `engines/nexus/hardening/gate_chain.py` (new)
- `engines/nexus/cards/routes.py`
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
- `engines/realtime/tests/*`
- `engines/nexus/hardening/rate_limit.py` (throttle durability only)

If a change would touch any other file, STOP.

## Phases to execute (in order)
1) PHASE_01_STREAMING_AUTH_AND_ISOLATION
2) PHASE_03_RAW_STORAGE_PRESIGN_REGISTER_FIX
3) PHASE_06_GATECHAIN_EXTERNAL_MUTATIONS
4) PHASE_08_REALTIME_REGISTRY_DURABILITY_THROTTLES

## STOP IF rules
- STOP if you need to modify any file outside the allowed list.
- STOP if adding new endpoints/schemas not present in code.
- STOP if auth/tenant enforcement would be weakened or bypassed.
- STOP if tests fail and require touching out-of-scope modules.

## PR breakdown
- 1 PR per phase above (4 PRs). Do not mix phases.

## Required tests per PR
- Phase 1: `pytest engines/chat/service/tests`
- Phase 3: `pytest engines/nexus/raw_storage/tests`
- Phase 6: `pytest engines/nexus/hardening/tests`
- Phase 8: `pytest engines/realtime/tests`
- Before merge of the last Lane A PR: run combined `pytest engines/chat/service/tests engines/nexus/raw_storage/tests engines/nexus/hardening/tests engines/realtime/tests`

## Acceptance / handoff checklist per PR
- Code limited to allowed files.
- Auth + RequestContext enforced where required; routing isolation validated.
- GateChain order preserved (KillSwitch → Firearms → StrategyLock/ThreeWise → Budget/KPI/Temperature → Audit emit) where applied.
- Raw storage keys use `tenants/{tenant_id}/{env}/...` and presign/register methods align.
- Tests listed above passed locally; attach command output summary.
- Note any touched shared module for integration (identity/auth/logging/contract files) so main owner can coordinate.
