# PHASE 03 — Projects + Threads Primitives

1. Goal
- Provide tenant/env-scoped Project and Thread primitives so switching project moves chat context; titles editable.

2. In scope
- Define Project and Thread models and repos.
- Routes: create/list/get/rename for projects and threads; role-gated (owner/admin for create/rename).
- Thread ties to project_id and surface_id/app_id.

3. Out of scope
- Chat orchestration logic; no prompts.
- KPI/Temperature/Strategy Lock/Firearms semantics changes.
- New env var names.

4. Hard boundaries (DO NOT TOUCH)
- 3D/video/audio engines.
- Any behavior logic beyond CRUD + scoping.
- Card/prompt logic in engines.

5. Affected modules
- engines/chat/service/ (for thread associations if applicable), engines/projects/* or new module for projects/threads.
- engines/identity/auth for auth checks (read-only).
- tests under engines/projects/tests/* (add) and engines/chat/tests if mounted.

6. API surface / routes
- POST /projects, GET /projects, GET /projects/{id}, PUT /projects/{id}/rename.
- POST /threads, GET /threads?project_id=..., GET /threads/{id}, PUT /threads/{id}/rename.
- All require tenant_id/env from context; membership/role enforcement.

7. Data model changes
- Project: id, tenant_id, env, title, created_at, updated_at, surface/app_id? optional.
- Thread: id, tenant_id, env, project_id, surface_id/app_id, title, created_at, updated_at.

8. Security & tenant binding
- require_tenant_membership on all; owner/admin for create/rename; members can list/get if same tenant/env.

9. Safety hooks
- Audit DatasetEvents for create/rename; no Strategy Lock/Firearms unless designated strategic (document if needed).

10. Observability
- Logs for create/rename with tenant/env/user/trace; metrics for counts by tenant.

11. Config / env vars
- Reuse existing storage/backends for persistence; no new env vars; fail if backend config missing.

12. Tests
- Pytests for CRUD + tenant isolation; role enforcement; thread must belong to project in same tenant/env; chat association if applicable.

13. Acceptance criteria
- Can create/list/rename projects and threads scoped to tenant/env; chat can attach thread_id/project_id without cross-tenant leakage.

14. Smoke commands
- curl -X POST /projects -H auth/tenant/env -d '{"title":"p1"}'
- curl -X POST /threads -H auth/tenant/env -d '{"project_id":"...","title":"t1"}'
