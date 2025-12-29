# PHASE_04_AUDIT_LOGGING_TRACE_IDS_IMMUTABILITY

## Goal
Swap the audit logger from a no-op into the Nexus logging engine, ensure every emitted `DatasetEvent` carries `trace_id`/`request_id` and `actor_type`, and guarantee persistence is immutable (no silent exceptions).

## In-scope / Out-of-scope
- **In-scope:** `engines/logging/audit.py`, `engines/logging/events/engine.py`, `engines/dataset/events/schemas.py` (if adding optional trace fields), `engines/logging/events/tests/*`, `engines/logging/audit/tests` (if created), any transport referencing `_audit_logger` (e.g., `engines/maybes/service.py`).
- **Out-of-scope:** Non-audit logging (console prints, Sentry hooks) and FE tracing.

## Required invariants
1. `_audit_logger` must delegate to `engines.logging.events.engine.run` so audit events pass through PII stripping and persistence, and any failure surfaces via exception or logged error.
2. Each `DatasetEvent` emitted for audits or control-plane actions must include `metadata["trace_id"]` and `metadata["request_id"]` drawn from `RequestContext.request_id`.
3. Actor type (human vs agent) is tagged on every event via `metadata["actor_type"]` or a dedicated field.
4. Train opt-out and PII stripping already happen before the backend write (phase 7 ensures persistence of opt-out). No event should silently drop during the audit pipeline.

## Allowed modules to change
- `engines/logging/audit.py`
- `engines/logging/events/engine.py`
- `engines/dataset/events/schemas.py`
- `engines/maybes/service.py` (to ensure audit helper usage still valid)
- `engines/logging/events/tests/*`
- `engines/maybes/tests/*` (only if verifying audit emission)

## Step-by-step tasks
1. Replace `_audit_logger` no-op with the real `engines.logging.events.engine.run` function, and ensure `emit_audit_event` passes along `metadata` containing `trace_id`, `request_id`, and `actor_type` derived from the `RequestContext`.
2. Update `engines/logging/events/engine.py` to log a warning if persistence fails instead of silently swallowing exceptions; return structured error data for callers to act on.
3. Expand `DatasetEvent` schema (if needed) to include optional `trace_id` or rely on metadata fields; document the requirement so downstream code can read it.
4. Update `engines/maybes/service.py` and any other audit emitters to pass the new metadata (request_id, actor_type) when calling `emit_audit_event` (already they pass context which contains request_id by default).
5. Add tests in `engines/logging/events/tests/test_logging_engine.py` verifying the event metadata includes `trace_id/request_id/actor_type` and that a backend exception surfaces to the caller.

## Tests
- `pytest engines/logging/events/tests/test_logging_engine.py::test_trace_id_attached`
- `pytest engines/logging/events/tests/test_logging_engine.py::test_audit_logger_failure_not_silent`
- `pytest engines/maybes/tests/test_service.py::test_audit_metadata_includes_request_id`

## Acceptance criteria
- Audits now go through the same PII/train_pref engine and persist to the configured Nexus backend; `_audit_logger` is no longer a no-op.
- Every emitted `DatasetEvent` includes `trace_id/request_id/actor_type` metadata so control-plane mutations can be traced end-to-end.
- Failures in the logging path raise or log errors rather than being swallowed, and tests confirm this behavior.

## Stop conditions
- Do not proceed if adding real audit persistence requires touching non-allowed modules to wire runtime_config or new dependencies; escalate first.
- Stop if `DatasetEvent` schema change forces widespread consumer updates beyond audit emitters.

## Do-not-touch list
- `engines/logging/event_log.py` (unless necessary and approved).
- `engines/dataset/events/tests` (unless directly impacted by schema additions).

## Mini execution guardrails
- If any change requires editing files outside the allowed modules, STOP before proceeding.
