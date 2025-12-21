# PHASE 08 — Stripe Billing: Checkout + Webhook + Entitlements + Comps

1. Goal
- Provide tenant-scoped billing with Stripe checkout, webhook handling, entitlements model, and comped-tenant override.

2. In scope
- Checkout session endpoint (owner/admin only) that creates Stripe session for the tenant.
- Webhook handler with signature verification; updates entitlements.
- Entitlements model per tenant/env; comp override flag.

3. Out of scope
- UI flows; pricing strategy.
- New env var names.
- Changes to Strategy Lock/Firearms semantics.

4. Hard boundaries (DO NOT TOUCH)
- KPI/Temperature semantics.
- 3D/video/audio engines.
- Prompts/cards/orchestration logic.

5. Affected modules
- engines/billing/* (routes/service/repo).
- engines/identity/auth for role checks.
- engines/logging/events for audit.
- tests under engines/billing/tests/*.

6. API surface / routes
- POST /billing/checkout (tenant_id from context; owner/admin) → returns Stripe session URL/id.
- POST /billing/webhook (Stripe signature verify) → updates entitlements.
- GET /billing/entitlements (tenant-scoped) → returns entitlement state including comp flag.

7. Data model changes
- Entitlement: tenant_id, env, plan_id, status, current_period_end, comped (bool), updated_at.
- BillingEvent log optional.

8. Security & tenant binding
- require_tenant_role owner/admin for checkout; webhook validates signature and maps to tenant via metadata.
- Tenant/env stored on entitlements; no cross-tenant updates.

9. Safety hooks
- DatasetEvents/audit for checkout initiated/completed, entitlements updated; Budget/Strategy Lock not changed.

10. Observability
- Metrics/logs for checkout requests, webhook outcomes, entitlement state changes; alert on signature failures.

11. Config / env vars
- Reuse canonical Stripe vars if present (STRIPE_API_KEY, STRIPE_WEBHOOK_SECRET). Missing keys must fail fast.

12. Tests
- Pytests for checkout role enforcement, webhook signature verification, entitlement update, comp override handling, tenant isolation.

13. Acceptance criteria
- Owner/admin can create checkout; webhook updates entitlements; comp flag can mark tenant as paid-free; tenant-scoped queries return correct state.

14. Smoke commands
- curl -X POST /billing/checkout -H auth/tenant/env -d '{"plan_id":"basic"}'
