# PHASE 02 — Auto-Tenant Bootstrap + Membership Stub

1. Goal
- Auto-create or attach tenant on first login/bootstrap without double-work; provide idempotent /auth/bootstrap path with owner membership creation.

2. In scope
- /auth/bootstrap route: if tenant missing, create tenant + owner membership; if exists, attach membership.
- Minimal invite model stub for future use (no full invite flows).
- Ensure tenant/env binding; role stored appropriately.

3. Out of scope
- Changing AuthContext/RequestContext shapes.
- Strategy Lock/Firearms semantics.
- New env var names; no prompts/orchestration.

4. Hard boundaries (DO NOT TOUCH)
- Strategy Lock, Firearms, KPI/Temperature semantics.
- 3D/video/audio engines.
- Card/prompt logic in engines.
- Env vars: reuse canonical tenant/auth config only.

5. Affected modules
- engines/identity/routes_auth.py (or relevant auth routes).
- engines/identity/service.py / repository for tenants/users/memberships.
- tests under engines/identity/tests/*.

6. API surface / routes
- /auth/bootstrap (POST): bearer token required; creates tenant + owner membership if none; otherwise ensures membership; returns tenant_id, user_id, role.
- /auth/me should reflect updated membership after bootstrap.

7. Data model changes
- Tenant and membership records: ensure tenant_id, env, user_id, role fields; invite stub model (id, email, tenant_id, role, status) optional placeholder.

8. Security & tenant binding
- Enforce membership creation only for the caller; owner role on new tenant; idempotent per user.
- Tenant/env derived from context; fail if missing.

9. Safety hooks
- DatasetEvent/audit for tenant creation/membership attachment with tenant/env/user/trace; no Strategy Lock/Firearms changes.

10. Observability
- Logs/metrics for tenant created vs reused; bootstrap errors with reasons.

11. Config / env vars
- Reuse existing auth/tenant config; no new names. Missing tenant storage config must fail.

12. Tests
- engines/identity/tests: bootstrap creates tenant + owner; second call idempotent; existing tenant attaches membership; tenant/env required; unauthorized fails.

13. Acceptance criteria
- New user with valid token hits /auth/bootstrap → gets tenant_id + owner role; repeated calls do not duplicate tenants; /auth/me shows membership.

14. Smoke commands
- curl -X POST http://localhost:8000/auth/bootstrap -H "Authorization: Bearer <JWT>" -H "X-Env: dev"
