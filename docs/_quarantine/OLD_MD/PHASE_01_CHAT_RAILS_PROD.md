# PHASE_01_CHAT_RAILS_PROD

## Goal
Harden chat realtime rails so WS/SSE require RequestContext + AuthContext, validate tenant/env via `verify_thread_access`, remove the duplicate unauth SSE router, and propagate request/trace metadata on events to eliminate cross-tenant leakage.

## Scope lock (allowed to change)
- `engines/chat/service/ws_transport.py`
- `engines/chat/service/sse_transport.py`
- `engines/realtime/isolation.py`
- `engines/chat/service/tests/*`
- `engines/common/identity.py` (only if needed to expose trace_id/request_id helper)
- DO NOT TOUCH: `engines/chat/service/http_transport.py`, muscle/video/audio engines, FE code.

## Invariants
- All chat WS/SSE endpoints depend on `get_request_context` + `get_auth_context`; reject missing/tenant mismatch before streaming.
- Routing keys validated via `verify_thread_access`; env must match RequestContext.
- No unauthenticated duplicate routers remain exported.
- Event envelopes include `routing.tenant_id/env/thread_id`, `meta.trace_id` (from RequestContext.request_id).

## Implementation checklist
1. Remove the legacy unauth SSE router at bottom of `sse_transport.py`; ensure only the authenticated router is exported.
2. WS: add RequestContext dependency (headers), align env/tenant with token, and enforce tenant/env match before `verify_thread_access`; attach `trace_id=request_context.request_id` into StreamEvent meta.
3. SSE: keep RequestContext/Auth deps; ensure `verify_thread_access` uses tenant/env; add `trace_id` into StreamEvent meta; handle Last-Event-ID passthrough.
4. Isolation: tighten `validate_routing` to require env match; ensure registry warnings remain.
5. Tests: add/extend in `engines/chat/service/tests` for 401 on missing auth, 403 on tenant mismatch, trace_id presence in payload, Last-Event-ID resume.

## Test plan
- `pytest engines/chat/service/tests/test_ws_transport.py`
- `pytest engines/chat/service/tests/test_sse_transport.py`
- What tests assert:
  - WS rejects missing/tenant-mismatched requests; events carry trace_id.
  - SSE rejects unauth; Last-Event-ID resumes; no unauth router.

## Worker Guardrails
- Allowed files: `engines/chat/service/ws_transport.py`, `engines/chat/service/sse_transport.py`, `engines/realtime/isolation.py`, `engines/chat/service/tests/*`, `engines/common/identity.py` (only if trace_id helper needed).
- If you need to change outside scope: STOP and report.
- No refactors; no formatting-only changes.
- FE/agents contract: requires `Authorization: Bearer <jwt>` + `X-Tenant-Id`, `X-Env` headers for RequestContext; SSE supports `Last-Event-ID` resume; events must include routing tenant/env/thread and `trace_id=request_id`.

## Smoke Test Gate
- Before and after changes run: `pytest engines/chat/service/tests/test_ws_transport.py engines/chat/service/tests/test_sse_transport.py`
- Pass = all tests green; failure means STOP and report.

## Negative tests required
- Add/ensure tests for cross-tenant access blocked (403 when thread tenant != RequestContext/Auth).
- Add/ensure tests for missing auth/context (401/400) on WS and SSE connect.

## Log + trace assertions
- StreamEvent meta must contain `trace_id` (RequestContext.request_id); routing must include tenant/env/thread_id; reject connections lacking these.
- SSE/WS events must not use `t_unknown` or missing env in routing.

## Acceptance criteria
- WS/SSE return 401/403 when auth/context invalid.
- Streamed events include routing tenant/env/thread and trace_id.
- No duplicate unauth SSE router remains.
- All listed tests pass.

## Stop conditions
- If changes require touching files outside scope, stop and escalate.
- If adding RequestContext breaks other routers (mount issues), halt and raise.

## Rollback notes
- Revert changed files to previous commit; ensure WS/SSE imports restored; remove new tests if added.

## PR slicing
- Single PR for Phase 1 (WS+SSE+tests+isolation tweaks).

Safe to hand to worker: YES (scope locked; clear tests; no schema inventions).
