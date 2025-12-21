# PHASE 1 — Maybes Audit + Contract Lock

DO NOT TOUCH:
- Strategy Lock, Firearms, Tenant/Auth shapes, Temperature/KPI semantics.
- 3D/video/audio engines.
- No new env vars; no prompts/agent logic in engines.

Allowed paths:
- docs/workflows/88mph/*, docs/infra/* (reference)
- engines/maybes/* (routes/service/repo/models/tests)
- engines/identity/auth.py (read-only reference)
- engines/logging/events.py, engines/dataset/events/schemas.py (reference only)

Tests to run:
- `python -m pytest engines/maybes/tests` (if present)
- Any new Maybes-specific tests added in this phase only.

Goal:
- Discover current Maybes implementation and lock a minimal v1 contract without altering other engines.

Plan tasks:
- Locate Maybes code (routes/service/repo/models/tests) and summarize existing behaviors and gaps.
- Define v1 contract: create/list/get/update/delete; tenant-scoped (note whether user-scoped exists/needed); raw text only; metadata (created_at, updated_at, source_refs, tags, pinned).
- Explicit boundaries: Maybes ≠ Nexus; content is runtime-visible; train/export controlled by train_ok flag (no content mutation for training).
- Document contract and gaps in this lane only.

Success criteria:
- Contract doc produced in this phase file; no code changes outside Maybes.
- Tests identified (or added) touch only Maybes.

Failure modes + rollback:
- If discovery shows breaking behavior, document as known issue; do not change Strategy Lock/Firearms/Auth/KPI/Temperature.

Agent prompt (run after reading above):
```
You are a coding agent.
Scope: PHASE 1 — Maybes Audit + Contract Lock (docs/workflows/88mph/PHASE_01_MAYBES_CONTRACT.md).
Tasks: audit engines/maybes/*, describe current behavior/gaps, write contract in this phase file (no other code changes unless adding Maybes-only tests), respect DO NOT TOUCH.
Tests: python -m pytest engines/maybes/tests (if exists).
Stop after contract is written and tests (if any) pass.
```
