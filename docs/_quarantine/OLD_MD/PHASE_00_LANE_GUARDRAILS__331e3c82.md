# PHASE 00 — Lane + Guardrails + Production Checklist

1. Goal
- Establish a single authoritative lane with guardrails and definition of done for production launch.

2. In scope
- Create/confirm this lane (README, CONTRACT, 00_MASTER_PLAN).
- Define production-ready checklist (auth, tenants, storage, billing, safety, observability, deploy checks).

3. Out of scope
- Any code changes in engines/tests/routes/configs.
- Adding prompts/orchestration logic.

4. Hard boundaries (DO NOT TOUCH)
- /engines code, tests, configs.
- 3D/video/audio engines.
- KPI/Temperature/Strategy Lock/Firearms semantics.
- Env var names (no new ones).

5. Affected modules
- docs/workflows/prod_launch/* only.

6. API surface / routes
- None (docs-only).

7. Data model changes
- None.

8. Security & tenant binding
- Document requirement: all routes/services must bind tenant_id + env (+ user where applicable); fail closed.

9. Safety hooks
- Document Strategy Lock/Firearms/Budget/Audit hook expectations; no code changes.

10. Observability
- Document requirement: DatasetEvent/audit logging for sensitive actions; fail on missing tenant/env/user/trace.

11. Config / env vars
- List canonical names as reference; no new names; missing config must cause startup/handler failure.

12. Tests
- None (docs-only).

13. Acceptance criteria
- Lane exists with README, CONTRACT, 00_MASTER_PLAN and production-ready checklist language.
- Guardrails are explicit so a feral agent cannot misinterpret scope.

14. Smoke commands
- None (docs-only).
