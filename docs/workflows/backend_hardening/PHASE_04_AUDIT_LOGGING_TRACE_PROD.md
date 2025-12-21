# PHASE_04_AUDIT_LOGGING_TRACE_PROD

## Goal
Turn on the audit pipeline by wiring `_audit_logger` to the DatasetEvent logging engine, propagate trace/request/actor metadata, and stop silent failures so audit/events are persisted with PII strip and training opt-out applied.

## Scope lock (allowed to change)
- `engines/logging/audit.py`
- `engines/logging/events/engine.py`
- `engines/dataset/events/schemas.py` (add optional trace/correlation fields if needed)
- `engines/logging/events/tests/*`
- `engines/maybes/service.py` (only to pass through metadata to audit)
- DO NOT TOUCH: GateChain, Nexus routes, chat transports.

## Invariants
- `_audit_logger` delegates to logging engine; no no-op defaults in prod path.
- Logging engine surfaces errors (no silent swallow) while keeping callers aware.
- DatasetEvent includes tenantId/env/agentId plus trace_id/request_id/actor_type in metadata or fields.
- PII strip + train_ok applied consistently.

## Implementation checklist
1. Update `emit_audit_event` to call logging engine with metadata containing request_id/trace_id (from RequestContext.request_id) and actor_type (human/agent).
2. Make logging engine log warnings/errors instead of silent except; ensure return structure signals failure.
3. Extend DatasetEvent schema if needed to carry trace_id/correlation_id; update writers accordingly.
4. Ensure callers (e.g., maybes) still pass through context; adjust tests for new metadata.
5. Add/extend tests to assert trace_id/actor metadata present and that exceptions surface (no silent pass).

## Test plan
- `pytest engines/logging/events/tests`
- `pytest engines/maybes/tests/test_service.py` (if updated)
- Tests assert audit goes through logging engine, metadata contains trace/actor, and failures are not swallowed.

## Worker Guardrails
- Allowed files: `engines/logging/audit.py`, `engines/logging/events/engine.py`, `engines/dataset/events/schemas.py`, `engines/logging/events/tests/*`, `engines/maybes/service.py` (metadata pass-through only).
- If you need to change outside scope: STOP and report.
- No refactors; no formatting-only changes.
- FE/agents contract: audit/events must emit tenantId/env/agentId with `trace_id`/`request_id`/`actor_type`; PII strip + train_ok still applied; no behavior change to existing response shapes.

## Smoke Test Gate
- Before/after run: `pytest engines/logging/events/tests`
- Pass = tests green; failures → stop.

## Negative tests required
- Ensure test covers backend error path causing audit emit to raise/log (no silent swallow).
- Ensure test for missing RequestContext/Auth in audit callers remains blocked (if applicable in maybes).

## Log + trace assertions
- DatasetEvents must include `trace_id`/`request_id`/`actor_type` (fields or metadata). Tests should assert presence in emitted event payload.

## Acceptance criteria
- Audit logger no longer a no-op; events hit logging engine.
- Trace/request/actor metadata present on emitted events.
- Logging engine does not silently drop errors.
- Tests pass.

## Stop conditions
- If schema changes force widespread client updates beyond scope, stop and escalate.
- If audit wiring requires new backends/config outside allowed files, halt.

## Rollback notes
- Revert logging/audit files and tests to prior revision.

## PR slicing
- Single PR for audit/trace wiring + tests.

Safe to hand to worker: YES (tight scope; explicit tests; no new APIs invented).
