# TENANTS, AUTH, AND BYOK (PLANNING)

Planning-only contract for tenant/user models, auth baseline, and BYOK connector handling with PII-safe constraints. No runtime code in this pass.

## Goals
- Baseline multi-tenant model and user auth shape.
- BYOK secret handling that keeps raw keys out of logs/Nexus.
- Align connector secret naming with `CONNECTORS_SECRETS_NAMING.md`.

## Tenant model (planning)
- Table `tenants` (conceptual):
  - `tenant_id` (`t_<slug>`), `display_name`
  - `plan_tier` (`free|pro|enterprise`), `billing_mode` (`os_paid|byok`)
  - `created_at`, `updated_at`
  - Optional: `status` (`active|suspended`), `notes`
- Tenant IDs follow the canonical pattern; env-specific tenants use suffixes (e.g., `t_northstar-dev`).

## User model (planning)
- Table `users`:
  - `user_id` (UUID), `tenant_id`
  - `email` (unique per tenant), `display_name`
  - `password_hash` (bcrypt/argon2 only; never stored or logged raw)
  - `role` (`owner|admin|member`), `created_at`, `updated_at`, `last_login_at`
- PII handling: emails/passwords are PII; redact in logs and DatasetEvents; use PII filter for auth flows.

## Auth baseline (planning)
- Endpoints:
  - `POST /auth/register` → create tenant + owner user (or attach to existing tenant) with hashed password.
  - `POST /auth/login` → verify password, issue JWT.
- JWT signing key stored in GSM as `auth-jwt-secret`; never checked into code or logs.
- Rate limits + captcha/abuse mitigation for auth endpoints (planning only).
- Session/trace logging must exclude raw passwords; include `request_id`, `tenant_id`, `user_id`.

## BYOK API (planning)
- Endpoints:
  - `POST /tenants/{tenant_id}/connectors/{provider}/{product}/{scope}/key`
    - Body: `{ "api_key": "<secret>" }`
    - Storage: secret in GSM as `tenant-<tenant_id>-<provider>-<product>-<scope>-key` (see CONNECTORS_SECRETS_NAMING.md).
    - DB metadata only: `has_byok`, `last_updated_at`, `masked_preview` (e.g., `sk-****abcd`).
  - `GET /tenants/{tenant_id}/connectors` → list metadata only (no raw secrets).
- OS-paid lanes read `conn-<provider>-<product>-<scope>-key`; BYOK lanes read tenant-scoped secrets.
- Explicit: raw keys never in logs, Nexus, DatasetEvents, or blackboards. Apply PII/redaction filters on request/response logging.

## PII/GDPR/UTM constraints
- Auth/BYOK handlers must route through the PII engine/redaction layer before logging or emitting DatasetEvents.
- UTM/event logging should carry only `request_id`, `tenant_id`, `connector_id`, status codes; no secrets or emails unless hashed.
- Future tests must assert logs/blackboards lack secrets/passwords.

## Non-goals (this pass)
- No implementation, storage migrations, or UI.
- No SSO/OAuth flows; only password/JWT baseline planned here.
