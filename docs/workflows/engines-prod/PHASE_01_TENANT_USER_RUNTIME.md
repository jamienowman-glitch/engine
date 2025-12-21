# PHASE 01 — Tenant/User Runtime

Goal:
- Enforce tenant/env/user scoping at every engine boundary and repository; default fail-closed when context is missing or mismatched.

Entry conditions:
- Identity/auth baseline present (`engines/identity/auth`, JWT parsing, request context helpers).
- Tenant/env headers or claims already passed through request context in calling surfaces.

In-scope (engines only):
- Validate `tenant_id` + `env` + `user_id` + role on all FastAPI routers/services (budget, kpi, temperature, nexus, vector_explorer, bossman, storage/media, analytics_events, logging).
- Ensure repositories and caches key by `(tenant_id, env, user_id where relevant)`; no cross-tenant globals.
- Normalize env tokens (`dev|staging|prod`) and enforce allowed set.
- Require `require_tenant_membership` for tenant routes; `require_tenant_role` for owner/admin actions.
- Fail loud when tenant/env/auth config is absent; no dev fallbacks.

Out-of-scope:
- New auth providers, OAuth flows, or behavior logic; no prompts/manifests/cards in engines.
- Changing KPI/Temperature meanings (only hardening is allowed in later phases).

Affected engine modules:
- `engines/identity/auth`, `engines/config/runtime_config`, `engines/common/request_context`.
- Routers/services: `budget`, `kpi`, `temperature`, `bossman`, `nexus`, `nexus/vector_explorer`, `logging/events`, `analytics_events`, `media/storage`, `page_content`, `kill_switch`, `strategy_lock`.
- Shared repos/cache layers that hold tenant data.

Runtime guarantees added:
- Every route/service rejects requests without tenant/env; role checks enforced where required.
- In-memory caches (if any) keyed by `(tenant_id, env)`; no leakage across tenants/users.
- Request/response logging redacts auth tokens; context propagated into DatasetEvents/Nexus writes.

What coding agents will implement later:
- Add boundary validators/middleware; standardize request context builder.
- Add isolation tests per feature proving tenant/user/env separation.
- Add config validation hooks that raise when tenant/env/auth slots are unset.

How we know it’s production-ready:
- Passing tests showing Tenant A cannot read/write Tenant B data for each feature area.
- Route contract docs require tenant/env headers/claims; smoke tests cover owner/admin/member permutations.
- No shared state survives across tenants in long-lived services.
