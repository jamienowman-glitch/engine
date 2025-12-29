# PHASE 3 — “Save to Maybe” + “Forward” Primitives

DO NOT TOUCH:
- Strategy Lock, Firearms, Tenant/Auth shapes, Temperature/KPI semantics.
- 3D/video/audio engines.
- No new env vars; no prompts/agent logic in engines.

Allowed paths:
- engines/maybes/* (routes/service/repo/models/tests)
- engines/identity/auth.py (for auth checks)
- engines/logging/events.py, engines/dataset/events/schemas.py (logging only)
- engines/chat/service/* (only if wiring optional route mounts; no orchestration changes)

Tests to run:
- `python -m pytest engines/maybes/tests`
- `python -m pytest engines/chat/tests` (only if router mounting touched; avoid changing chat behavior)

Goal:
- Add backend-only primitives for “save message to maybe” and “forward bundle” without altering chat orchestration.

Plan tasks:
- Add endpoint to save raw text + source refs to a Maybe (tenant-scoped, membership-gated).
- Add endpoint to create a “forward bundle” record (or stub pointer) without changing chat flows; store minimal metadata only.
- Ensure both endpoints enforce tenant membership/role as needed; no strategy/firearms changes unless explicitly gated.
- Log DatasetEvents with tenant/env/user/trace; keep content deterministic (no summarization/LLM).
- Add isolation tests proving tenant gating; ensure chat wiring is optional and does not change behavior.

Success criteria:
- Endpoints exist and are auth-gated; no chat orchestration changes.
- Tests show tenant isolation and membership enforcement.
- No violations of DO NOT TOUCH areas.

Failure modes + rollback:
- If chat tests break due to router mounts, revert mounting and document as known issue; do not alter chat logic.
- If Strategy Lock/Firearms needed, only hook (no semantic changes) or document gap.

Agent prompt (run after reading above):
```
You are a coding agent.
Scope: PHASE 3 — “Save to Maybe” + “Forward” Primitives (docs/workflows/88mph/PHASE_03_MAYBES_PRIMITIVES.md).
Tasks: add tenant-scoped endpoints to save raw text to Maybe and to create a forward bundle stub; auth-gate via membership; log DatasetEvents. Do not change chat orchestration logic or any DO NOT TOUCH areas. Use existing env vars only.
Tests: python -m pytest engines/maybes/tests [plus engines/chat/tests if routers mounted].
Stop when endpoints and tests are done.
```
