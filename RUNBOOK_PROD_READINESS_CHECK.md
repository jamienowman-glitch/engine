# RUNBOOK_PROD_READINESS_CHECK

Use this checklist after phases 01–07 land. All items must tick “YES” before declaring prod-ready.

## Rails & Auth
- [ ] Chat WS/SSE require RequestContext + AuthContext; routing tenant/env/thread validated; no `t_unknown`; trace_id in events.
- [ ] Chat HTTP requires RequestContext/Auth; DatasetEvents carry real tenant/env/request_id.
- [ ] Nexus routes (raw_storage, atoms, packs, cards, index, settings, runs, memory) enforce AuthContext + tenant membership + assert_context_matches.

## Storage
- [ ] Raw storage presign/register uses `tenants/{tenant}/{env}/raw/...` keys; auth enforced; audit/event emitted with trace/request IDs.
- [ ] media_v2 and canvas artifacts enforce tenant/env prefixes; prod does not fall back to local temp paths.

## Audit/Logging
- [ ] Audit logger wired to logging engine; no no-op defaults; errors not swallowed.
- [ ] DatasetEvents include tenant/env/agentId and trace_id/request_id/actor_type; PII strip + train_ok applied.

## GateChain
- [ ] GateChain exists and is applied to external mutation endpoints (raw_storage register, cards, settings, runs, memory, maybes mutations, analytics_events writes).
- [ ] Gate order: KillSwitch → Firearms → StrategyLock/ThreeWise → Budget/KPI/Temperature → Audit emit.

## Safety leaks closed
- [ ] Temperature `/config` requires AuthContext.
- [ ] No unauth SSE router present; chat pipeline no longer uses `t_unknown`.

## Testing
- [ ] Chat tests: `pytest engines/chat/service/tests`
- [ ] Nexus tests: `pytest engines/nexus/raw_storage/tests engines/nexus/atoms/tests engines/nexus/packs/tests engines/nexus/cards/tests engines/nexus/index/tests engines/nexus/settings/tests engines/nexus/runs/tests engines/nexus/memory/tests`
- [ ] Raw storage tests: `pytest engines/nexus/raw_storage/tests`
- [ ] Audit/logging tests: `pytest engines/logging/events/tests`
- [ ] GateChain tests: `pytest engines/nexus/hardening/tests`
- [ ] Storage prefix tests: `pytest engines/media_v2/tests/test_media_v2_endpoints.py engines/canvas_artifacts/tests/test_artifacts.py`
- [ ] Leaks cleanup tests: `pytest engines/temperature/tests/test_temperature_routes.py engines/chat/tests`

## Verification notes
- If any test fails, stop and fix before proceeding.
- If any item cannot be ticked due to missing data/config (e.g., KPI/Temperature metrics), document and set feature flags before prod rollout.
