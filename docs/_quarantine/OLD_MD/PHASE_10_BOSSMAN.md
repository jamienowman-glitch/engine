# PHASE 10 — Bossman Launch Dashboard v2

1. Goal
- Provide a single owner/admin dashboard endpoint showing auth/storage/billing/spend/safety status for production launch.

2. In scope
- Read-only Bossman dashboard aggregation of status/health fields: Cognito config/reachability, S3 config/last write probe, Stripe config/last webhook, budgets/COGS by provider, strategy locks/licenses/kill switches.
- Freshness timestamps for each subsystem; sink/backend indicators.

3. Out of scope
- Changing underlying behaviors of auth/storage/billing/budget/safety.
- New env var names.
- Prompts/orchestration logic.

4. Hard boundaries (DO NOT TOUCH)
- KPI/Temperature semantics.
- 3D/video/audio engines.
- Strategy Lock/Firearms semantics (read-only display).

5. Affected modules
- engines/bossman/routes.py (dashboard read model).
- engines/budget/* (read-only), engines/kill_switch/* (read-only), engines/strategy_lock/* (read-only), engines/firearms/* (read-only), engines/billing/* (read-only), engines/config/runtime_config.py (read-only), engines/storage status probes, engines/logging/events (if logging needed).
- tests under engines/bossman/tests/*.

6. API surface / routes
- GET /bossman/launch-dashboard (owner/admin only): returns auth/storage/billing/spend/safety status, freshness timestamps, backend identifiers.

7. Data model changes
- Dashboard payload only; no persistent model changes required.

8. Security & tenant binding
- require_tenant_role owner/admin; tenant/env scoped responses; no cross-tenant data.

9. Safety hooks
- Read-only; ensure data displayed reflects gate states (strategy lock, kill switches, licences).

10. Observability
- Logs for dashboard requests with tenant/env/user/trace; metrics for load/errors; optional DatasetEvent for dashboard view.

11. Config / env vars
- Reuse existing config names (Cognito, S3, Stripe, budget backends). Missing config should surface as unhealthy with clear message (fail loud).

12. Tests
- Pytests for endpoint role enforcement, freshness fields present, indicators reflect stubbed statuses, tenant isolation.

13. Acceptance criteria
- Owner/admin can fetch dashboard showing auth/storage/billing/spend/safety status with freshness/backends; no cross-tenant leakage; missing config shows unhealthy.

14. Smoke commands
- curl -H auth/tenant/env http://localhost:8000/bossman/launch-dashboard
