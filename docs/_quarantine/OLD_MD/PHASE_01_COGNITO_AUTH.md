# PHASE 01 — Cognito Auth: Real JWT Verify + /auth/me

1. Goal
- Accept real Cognito RS256 tokens, verify via JWKS (no mocks), and expose /auth/me returning canonical AuthContext + derived RequestContext with tenant binding.

2. In scope
- JWT verification flow using Cognito issuer/audience.
- /auth/me route returning decoded claims + derived RequestContext/AuthContext fields.
- JWKS caching/rotation and strict exp/iss/aud checks.
- Tenant membership/role enforcement at boundaries.

3. Out of scope
- Changing AuthContext/RequestContext shapes.
- Adding prompts/orchestration logic.
- New env var names; no mock auth shortcuts.

4. Hard boundaries (DO NOT TOUCH)
- Strategy Lock, Firearms, KPI/Temperature semantics.
- 3D/video/audio engines.
- Any card/prompt logic in engines.
- Env var names: reuse existing (auth_jwt_signing, etc.); no new names.

5. Affected modules
- engines/identity/auth.py, engines/identity/routes_auth.py (or current auth routes).
- engines/config/runtime_config.py (read existing getters; no new vars).
- docs/infra/AUTH_TENANT_SPINE_DEV_RUN.md (reference).
- tests under engines/identity/tests/*.

6. API surface / routes
- /auth/me (GET): bearer token required; returns AuthContext + RequestContext (tenant_id, env, user_id/auth_subject, membership_role, request_id/trace_id).
- Ensure existing protected routes reuse verified context.

7. Data model changes
- None; reuse existing user/tenant/membership models.

8. Security & tenant binding
- Verify RS256 JWT via Cognito JWKS; enforce iss/aud; fail closed on missing/invalid token.
- Derive tenant_id/env from claims or headers as currently defined; membership/role checks enforced at route dependency.

9. Safety hooks
- Audit DatasetEvent on auth/me? Optional; if added, log tenant/env/user/trace only (no PII). No Strategy Lock/Firearms changes.

10. Observability
- Metrics/logs for auth failures vs successes; cache hit/miss for JWKS; include tenant/env/user_id when resolved.

11. Config / env vars
- Reuse existing auth vars: auth_jwt_signing slot, issuer/audience config if present. Missing JWKS/issuer/audience must raise at startup or first request.

12. Tests
- Add/extend pytest in engines/identity/tests: valid token passes; bad iss/aud/exp fails; JWKS rotation respected; /auth/me returns expected fields.

13. Acceptance criteria
- Using a real Cognito token, /auth/me returns correct context; invalid tokens 401/403.
- Protected routes reject missing/invalid tokens; tenant binding present.

14. Smoke commands
- curl -H "Authorization: Bearer <JWT>" http://localhost:8000/auth/me
- curl protected endpoint with valid vs invalid token and observe 200 vs 401/403.
