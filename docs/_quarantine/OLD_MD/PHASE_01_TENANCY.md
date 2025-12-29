# PHASE 01 — Tenancy Baseline: Tenant-0 + Tenant-1 (Northstar)

Goal: Real multi-tenant baseline with Tenant-0 control plane and Tenant-1 (Northstar) behaving like any tenant. Provide feature-flag surface for rail switches. Tenant IDs must follow existing pattern `t_<slug>` (see `engines/common/identity.py` validator; dev secret `northstar-dev-tenant-0-id` maps to `t_northstar-dev`).

In-scope
- Bootstrap paths for creating/identifying Tenant-0 and Tenant-1 using existing identity repo/routes.
- Feature flag/control switches scoped to Tenant-0 for: WS vs SSE rail selection, gesture logging mode, replay mode, visibility modes.
- Auth + RequestContext enforcement on all new control surfaces.

Out-of-scope
- UI, orchestration, prompts, tool personas.
- New storage providers; reuse existing `RAW_BUCKET`/`DATASETS_BUCKET` envs (S3 default) without changing naming.

Allowed modules to change
- `engines/identity/*` (routes_auth, models, repository) to codify Tenant-0/1 bootstrap.
- `engines/common/identity.py` (if needed for Tenant-0 marker).
- `engines/config/runtime_config.py` or new `engines/feature_flags/*` module for control flags.
- Tests under `engines/identity/tests` or new `engines/feature_flags/tests`.

Steps
1) Define Tenant-0 and Tenant-1 bootstrap:
   - Add deterministic creation path using identity repo (owner membership). Tenant-0 = system/operator; Tenant-1 = Northstar (100% discount, but pricing logic out-of-scope). IDs must be `t_*` and align with existing GSM secret naming (e.g., `northstar-dev-tenant-0-id`).
   - Expose bootstrap endpoint(s) gated by admin token or environment guard (reuse `get_auth_context`).
2) Feature flag surface for Tenant-0:
   - Add small model/repo for feature toggles (WS vs SSE, gesture logging mode, replay mode, visibility modes).
   - Add routes under `/feature-flags` (Tenant-0 only) enforcing RequestContext + owner/admin.
3) Enforce RequestContext/auth on new routes; ensure role checks (owner/admin) guard flag updates.
4) Tests:
   - Bootstrap creates tenants with roles, asserts Tenant-0 != Tenant-1.
   - Flag CRUD enforces tenant/role isolation; non-owner blocked.
5) Stop conditions:
   - DO NOT continue if flags are not tenant-scoped or if Tenant-0 writes leak to other tenants.
   - DO NOT continue if auth/RequestContext is bypassed anywhere in new routes.

Do not touch
- No changes to FE, no orchestration manifests, no chat/render behavior beyond adding auth/tenant guards for new surfaces.
