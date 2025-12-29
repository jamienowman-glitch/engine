# Phase 0 Mode-Only RequestContext Delta (engines truth)

Current state (engines/common/identity.py:22-151)
- Required: tenant_id (regex ^t_[a-z0-9_-]+$), env (dev/staging/prod/stage→staging), project_id (400 if missing), request_id auto.
- Optional/defaulted: surface_id/app_id via identity_repo (lines 120-136), user_id, membership_role.
- Headers: X-Tenant-Id, X-Env, X-Project-Id, X-Surface-Id, X-App-Id, X-User-Id, X-Membership-Role, X-Request-Id (lines 43-51).
- Fallbacks: query params for tenant/env/user/project/surface/app (lines 53-58); body fallback if still missing (lines 82-102).
- JWT overlay: Authorization bearer decoded; fills tenant/user/role; rejects tenant not in membership (lines 73-115).

Contract to enforce (mode-only)
- Replace X-Env with X-Mode; accepted values exactly saas|enterprise|lab. Reject legacy env values.
- RequestContext must require mode; no body fallback unless gated legacy flag; headers preferred, query fallback only under explicit compatibility flag.
- tenant_id always required; only hardcoded tenant allowed: t_system (bootstrap: engines/identity/routes_auth.py:82-107).
- Surface/app defaults may remain but must be mode-aware and fail if absent.
- SSE/WS must carry same headers; Authorization required (sse_transport.py:44-58; ws_transport.py:136-160) — extend to enforce mode/project/app.

Rejection behavior (must implement)
- If X-Mode missing or not in {saas, enterprise, lab} → 400.
- If legacy X-Env provided → 400 (unless explicit legacy flag set to migrate).
- If project_id missing → 400 (retain current check).
- If tenant not in token memberships → 403 (retain current).
