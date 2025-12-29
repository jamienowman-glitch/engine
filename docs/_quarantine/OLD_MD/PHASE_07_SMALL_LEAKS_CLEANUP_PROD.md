# PHASE_07_SMALL_LEAKS_CLEANUP_PROD

## Goal
Close remaining leaks: enforce auth on temperature config read, stop chat pipeline from emitting events under `t_unknown` by requiring RequestContext/auth on chat HTTP transport, and ensure chat DatasetEvent logging uses real tenant/env/request IDs.

## Scope lock (allowed to change)
- `engines/temperature/routes.py` (auth for `/config`)
- `engines/chat/service/http_transport.py`
- `engines/chat/pipeline.py`
- Tests under `engines/temperature/tests`, `engines/chat/tests`
- DO NOT TOUCH: WS/SSE transports (handled in Phase 1), Nexus routes (Phase 2), audit/logging internals (Phase 4).

## Invariants
- `GET /temperature/config` requires AuthContext + tenant membership; no unauth read.
- Chat HTTP transport requires RequestContext + AuthContext; rejects unauth; no default `t_unknown`.
- Chat pipeline derives tenant/env/request_id from RequestContext or AuthContext, not runtime_config defaults.

## Implementation checklist
1. Add AuthContext dependency + membership check to `temperature/routes.py:get_config`; keep RequestContext.
2. Add RequestContext + AuthContext dependencies to chat HTTP routes (threads/messages) and enforce tenant match.
3. Update chat pipeline to accept/require RequestContext and use it for DatasetEvent tenant/env/request_id; fail fast if missing in prod mode (no `t_unknown` fallback).
4. Add tests: temperature config requires auth; chat HTTP rejects missing auth/tenant mismatch; chat pipeline logs correct tenant/env.

## Test plan
- `pytest engines/temperature/tests/test_temperature_routes.py`
- `pytest engines/chat/tests/test_schemas_basic.py` (or new chat HTTP auth tests)
- `pytest engines/chat/tests/test_actions_basic.py` (if extended) or new pipeline tests
- Tests assert auth enforcement and absence of `t_unknown` tenant emissions.

## Worker Guardrails
- Allowed files: `engines/temperature/routes.py`, `engines/chat/service/http_transport.py`, `engines/chat/pipeline.py`, `engines/temperature/tests/*`, `engines/chat/tests/*` (only for new/updated tests about auth/context and pipeline tenant correctness).
- If you need to change outside scope: STOP and report.
- No refactors; no formatting-only changes.
- FE/agents contract: temperature config now requires `Authorization` + RequestContext; chat HTTP requires RequestContext/Auth headers; DatasetEvents from chat must carry real tenant/env/request_id (no `t_unknown` fallback).

## Smoke Test Gate
- Before/after run: `pytest engines/temperature/tests/test_temperature_routes.py engines/chat/tests`
- Pass = tests green; failures → stop.

## Negative tests required
- Temperature config unauth/mismatched tenant returns 401/403.
- Chat HTTP missing auth/context rejected; cross-tenant access blocked.

## Log + trace assertions
- Chat pipeline events must include RequestContext.request_id as trace_id/metadata and tenant/env matching context; ensure tests assert absence of `t_unknown`.

## Acceptance criteria
- Temperature config read 401/403 without valid auth/tenant.
- Chat HTTP endpoints require RequestContext/Auth; no default tenant.
- DatasetEvents from chat pipeline carry real tenant/env/request_id; no `t_unknown`.
- Tests pass.

## Stop conditions
- If enforcing auth requires touching shared mounts beyond scope, stop.
- If chat pipeline contract change impacts FE without confirmation, halt and flag.

## Rollback notes
- Revert temperature/chat files and tests to prior revision.

## PR slicing
- Single PR for small leaks cleanup + tests.

Safe to hand to worker: YES (bounded files; clear asserts).
