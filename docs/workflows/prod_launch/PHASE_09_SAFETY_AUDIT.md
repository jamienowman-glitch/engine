# PHASE 09 — Safety/Audit/Prod Gate Sweep + Fail-Fast Config

1. Goal
- Ensure safety gates, audit logging, and config validation are production-ready and fail fast (no silent fallbacks).

2. In scope
- Confirm Strategy Lock/Firearms gating on behavior/cost/risk writes (no semantic changes; hook verification only).
- Confirm kill-switch enforcement on spend-related paths.
- Ensure audit/DatasetEvents for sensitive actions (auth, tenant changes, billing, storage writes).
- Add fail-fast config checks for required env/slots across auth/storage/billing/safety.

3. Out of scope
- Changing gate semantics or policies.
- New env var names.
- Prompts/orchestration logic.

4. Hard boundaries (DO NOT TOUCH)
- KPI/Temperature semantics.
- 3D/video/audio engines.
- Strategy Lock/Firearms logic (verify only).

5. Affected modules
- engines/strategy_lock/* (read-only verification), engines/firearms/* (read-only), engines/kill_switch/*, engines/logging/events, engines/config/runtime_config.py, engines/budget/* (for spend enforcement visibility), docs/infra/AUTH_TENANT_SPINE_DEV_RUN.md.

6. API surface / routes
- No new endpoints unless needed for health/config check; if added, read-only status endpoints only.

7. Data model changes
- None beyond possible config status structures.

8. Security & tenant binding
- Verify membership/role enforcement remains intact on sensitive routes; document gaps.

9. Safety hooks
- Validate Strategy Lock/Firearms hooks present where required; kill-switch consulted before spend; document missing hooks.

10. Observability
- Ensure DatasetEvents/audit for sensitive actions; add metrics/logs for missing config detection; status indicators for gates.

11. Config / env vars
- List required envs (auth, storage, billing, safety). Missing values must raise at startup or first call; no defaults.

12. Tests
- Pytests to assert fail-fast on missing config, gate checks invoked, audit events emitted on sensitive routes; no semantic changes to gates.

13. Acceptance criteria
- Safety gates verified and documented; missing hooks identified or added without changing semantics.
- Config missing → controlled failure with clear error.
- Audit events present for sensitive actions; kill-switch enforced on spend paths.

14. Smoke commands
- Negative tests: unset required env and ensure service fails to start or endpoint 500s with clear message.
