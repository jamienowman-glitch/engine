# Auth / Tenant Spine (Dev Run)

Phase-1 backend-only spine for multi-tenant/user handling and future BYOK wiring.

## Models (engines/identity)
- **User**: `id`, `email`, `display_name?`, `avatar_url?`, `password_hash`, timestamps.
- **Tenant**: `id`, `name`, `status` (`active|disabled|suspended`), `created_by`, timestamps.
- **TenantMembership**: `id`, `tenant_id`, `user_id`, `role` (`owner|admin|member|viewer`), `status` (`active|pending|revoked`), timestamps.
- **TenantKeyConfig**: `id`, `tenant_id`, `env`, `slot`, `provider`, `secret_name` (GSM secret id), `metadata{}`, timestamps.
- Repositories: `InMemoryIdentityRepository` implements the CRUD interface; Firestore can be added later without changing callers.

## RequestContext (engines/common/identity.py)
- `RequestContext`: `request_id`, `tenant_id`, `env` (`dev|staging|prod`), optional `user_id`, `membership_role`, `auth_subject`, `is_system`.
- `get_request_context` FastAPI dependency:
  - Sources `tenant_id`/`env` from headers (`X-Tenant-Id`, `X-Env`) or query params (`tenant_id`, `env`).
  - Falls back to JSON body fields for legacy POST flows.
  - Optional `X-User-Id`, `X-Membership-Role`, `X-Request-Id`.
  - Normalises `stage` -> `staging`; raises 400 on mismatch/absence.
- `assert_context_matches` ensures any explicit tenant/env params match the resolved context.
- Production paths do not fall back to `t_unknown`; tenant/env must be supplied via `RequestContext` (headers/query/body).

## Key selection (engines/common/keys.py)
- Slot-based selection via `TenantKeySelector.get_config(tenant_id, env, slot)`:
  - Lookup order: (tenant, env, slot) → (tenant, prod, slot) → (system, env, slot) → (system, prod, slot).
  - Returns `KeyMaterial {provider, secret, metadata, config}`; raises `MissingKeyConfig` if nothing matches.
  - Secrets are read from Google Secret Manager using `secret_name`; errors map to `SecretNotFound` / `SecretManagerError`.
  - Dev-only escape hatch: if GSM is missing and `APP_ENV` is `local/dev/staging`, a slot-named env var may be used; prod must use GSM.
  - `SYSTEM_TENANT_ID = "system"` holds OS defaults when per-tenant slots are absent.
- Canonical slots: `llm_primary`, `embed_primary`, `vector_store_primary`, `auth_jwt_signing`, `metrics_primary`.
- runtime_config + SELECTA: metadata on slots feeds runtime helpers (prod must use slots; dev/local can fall back to env vars):
  - `vector_store_primary.metadata`: `project`, `region`, `index_id`, `endpoint_id`.
  - `embed_primary.metadata`: `model`/`model_id`.
  - `auth_jwt_signing` secret is used for JWT signing; `metrics_primary` reserved for external metrics adapters.
- Slot setup examples (dev):
  - `curl -X POST http://localhost:8000/tenants/t_demo/keys -H "X-Tenant-Id: t_demo" -H "X-Env: dev" -H "Content-Type: application/json" -d '{"slot":"llm_primary","env":"dev","provider":"openai","secret_value":"sk-...","metadata":{"model":"gpt-4.1"}}'`
  - `curl -X POST http://localhost:8000/tenants/t_demo/keys -H "X-Tenant-Id: t_demo" -H "X-Env: dev" -H "Content-Type: application/json" -d '{"slot":"embed_primary","env":"dev","provider":"vertex","secret_value":"unused-for-vertex","metadata":{"model_id":"text-embedding-004"}}'`
  - `curl -X POST http://localhost:8000/tenants/t_demo/keys -H "X-Tenant-Id: t_demo" -H "X-Env: dev" -H "Content-Type: application/json" -d '{"slot":"vector_store_primary","env":"dev","provider":"vertex","secret_value":"unused","metadata":{"project":"my-proj","region":"us-central1","index_id":"idx123","endpoint_id":"ep123"}}'`

## Analytics configs (tenant + OS)
- Model: `TenantAnalyticsConfig` (tenant_id, env, surface, ga4_measurement_id, ga4_api_secret_slot, meta/tiktok/snap pixel ids, extra, timestamps).
- Storage: in-memory by default; Firestore when `IDENTITY_BACKEND=firestore`. Secrets (GA4 API secret) should live in GSM slots via `ga4_api_secret_slot`.
- Routes (auth required):
  - `PUT /tenants/{tenant_id}/analytics/config` — upsert for a surface/env (tenant owner/admin).
  - `GET /tenants/{tenant_id}/analytics/config` — list configs (tenant membership).
  - `GET /tenants/{tenant_id}/analytics/config/current?env=...&surface=...` — resolves effective config with fallback `tenant/env` → `tenant/prod` → `system/env` → `system/prod`.
- Resolver: `engines/common/analytics.AnalyticsResolver.resolve(ctx, surface)` returns `EffectiveAnalyticsConfig{... source=tenant|system}` for builders/connectors.
- Example payloads:
  - OS marketing (system tenant): `{"tenant_id":"system","env":"prod","surface":"northstar_marketing","ga4_measurement_id":"G-OS123","ga4_api_secret_slot":"ga4_api_secret_prod","meta_pixel_id":"1234567890"}`
  - Tenant surface: `{"tenant_id":"t_demo","env":"dev","surface":"squared","ga4_measurement_id":"G-DEMO1","meta_pixel_id":"987654321"}`
- Example curl (dev):
```
curl -X PUT http://localhost:8000/tenants/t_demo/analytics/config \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-Id: t_demo" -H "X-Env: dev" \
  -H "Content-Type: application/json" \
  -d '{"tenant_id":"t_demo","env":"dev","surface":"squared","ga4_measurement_id":"G-DEMO1","ga4_api_secret_slot":"ga4_api_secret_dev","meta_pixel_id":"1234"}'
```

## Secret storage (engines/common/secrets.py)
- GSM helper wraps `google-cloud-secretmanager`:
  - `access_secret(secret_id)` → latest version contents.
  - `create_or_update_secret(secret_id, value)` → creates if missing, adds new version otherwise.
  - Canonical secret id: `canonical_secret_id(tenant_id, env, slot)` → `"tenants-{tenant}-env-{env}-slot-{slot}"` (slash-safe).
- Env for GSM auth comes from ADC/workload identity; no raw keys are read from env in prod.
- Prod rule: secrets must be created via the key slot API; env-var fallbacks are dev-only.

## Routing updates (dev-only)
- **MAYBES** (`engines/maybes/routes.py`):
  - Routes depend on `get_request_context`; tenant/env from context must match params.
  - Services/repositories now receive tenant/env from `RequestContext` instead of arbitrary inputs.
- **Vector Explorer** (`engines/nexus/vector_explorer/routes.py`):
  - Routes depend on `get_request_context`; tenant/env alignment is enforced.
  - Repository lookups now take tenant/env explicitly to avoid cross-tenant leakage.
  - No `t_unknown` fallback; missing tenant/env returns 4xx.
  - Requires bearer JWT with tenant membership.
- **Tenant key slots API** (`engines/identity/routes_keys.py`):
  - `GET /tenants/{tenant_id}/keys` → list configs (no secrets).
  - `GET /tenants/{tenant_id}/keys/{slot}?env=...` → one config (no secret).
  - `POST /tenants/{tenant_id}/keys` / `PUT /tenants/{tenant_id}/keys/{slot}` with body:
    - `{ slot, env, provider, secret_value, metadata? }`
    - Writes GSM secret at `canonical_secret_id(tenant, env, slot)` and stores `TenantKeyConfig` pointing to it.
  - TODO: enforce tenant-admin auth when JWT/roles arrive.

## Next steps (later phases)
- Parse JWTs (Cognito/Google/Apple) to populate `auth_subject`, `user_id`, and memberships.
- Add Firestore/SQL repositories for identity and key configs.
- Enforce tenant-admin auth on key routes; expose Secrets Console UI that calls these endpoints.

## Examples (dev)
- Create slot: `curl -X POST http://localhost:8000/tenants/t_demo/keys -H "X-Tenant-Id: t_demo" -H "X-Env: dev" -H "Content-Type: application/json" -d '{"slot":"llm_primary","env":"dev","provider":"openai","secret_value":"sk-...","metadata":{"region":"us-central1"}}'`
- List slots: `curl -H "X-Tenant-Id: t_demo" -H "X-Env: dev" http://localhost:8000/tenants/t_demo/keys`
- Fetch slot: `curl -H "X-Tenant-Id: t_demo" -H "X-Env: dev" "http://localhost:8000/tenants/t_demo/keys/llm_primary?env=dev"`

## Temperature primitives (engines/temperature)
- Models:
  - `FloorConfig`: tenant/env/surface with `performance_floors{metric->min}` and `cadence_floors{metric->min}`.
  - `CeilingConfig`: tenant/env/surface with `ceilings{metric->max}`.
  - `TemperatureWeights`: tenant/env/surface with `weights{metric->weight}`, `source` (`system_default|tenant_override|llm_tuned`).
  - `TemperatureSnapshot`: tenant/env/surface, `value`, window, breached floor/ceiling lists, raw_metrics, `source`, timestamps.
- API:
  - `PUT /temperature/floors` — upsert floors for tenant/env/surface.
  - `PUT /temperature/ceilings` — upsert ceilings.
  - `PUT /temperature/weights` — upsert weights.
  - `GET /temperature/config?surface=...` — combined config bundle.
  - `GET /temperature/current?surface=...&window_days=7` — compute + persist snapshot (deterministic).
- `GET /temperature/history?surface=...&limit=...&offset=...` — list recent snapshots.
- Concepts:
  - Performance floors: minimum outcome metrics (e.g., weekly_leads).
  - Cadence floors: minimum frequency (e.g., email_campaigns_per_week).
  - Ceilings: upper bounds to avoid runaway actions (e.g., max_emails_per_day, complaint_rate).
  - Temperature: scalar derived from metrics vs floors/ceilings using weights; today deterministic; weekly LLM tuning will adjust weights later.
- Example curls:
  - Floors: `curl -X PUT http://localhost:8000/temperature/floors -H "X-Tenant-Id: t_demo" -H "X-Env: dev" -H "Content-Type: application/json" -d '{"tenant_id":"t_demo","env":"dev","surface":"squared","performance_floors":{"weekly_leads":50},"cadence_floors":{"email_campaigns_per_week":3}}'`
  - Ceilings: `curl -X PUT http://localhost:8000/temperature/ceilings -H "X-Tenant-Id: t_demo" -H "X-Env: dev" -H "Content-Type: application/json" -d '{"tenant_id":"t_demo","env":"dev","surface":"squared","ceilings":{"complaint_rate":0.05}}'`
  - Weights: `curl -X PUT http://localhost:8000/temperature/weights -H "X-Tenant-Id: t_demo" -H "X-Env: dev" -H "Content-Type: application/json" -d '{"tenant_id":"t_demo","env":"dev","surface":"squared","weights":{"weekly_leads":1.0,"email_campaigns_per_week":0.5},"source":"tenant_override"}'`
  - Current: `curl -H "X-Tenant-Id: t_demo" -H "X-Env: dev" "http://localhost:8000/temperature/current?surface=squared&window_days=7"`
  - History: `curl -H "X-Tenant-Id: t_demo" -H "X-Env: dev" "http://localhost:8000/temperature/history?surface=squared&limit=10"`

## Auth / JWT (dev baseline)
- Models: Tenant (id, name, status, created_by), User (id, email, display_name?, avatar_url?, password_hash), TenantMembership (tenant_id, user_id, role, status).
- JWT claims: `sub`, `email`, `tenant_ids[]`, `default_tenant_id`, `role_map{tenant_id: role}`. Signed with HS256 via key slot `auth_jwt_signing` under system tenant (fallback to `AUTH_JWT_SIGNING` env var in dev).
- Routes:
  - `POST /auth/signup` — create user (+ tenant + owner membership when `tenant_name` provided), returns JWT + user/tenant/memberships.
  - `POST /auth/login` — email+password, returns JWT + user info.
  - `POST /auth/refresh` — re-issue token from existing bearer.
  - `GET /auth/me` — decodes token.
- Protected routes/roles:
  - `/tenants/{tenant_id}/keys` and `/temperature/floors|ceilings|weights` require bearer token with role owner|admin for that tenant.
  - Temperature compute/history requires membership for tenant.
  - MAYBES/Vector Explorer still accept tenant headers; TODO: tighten to JWT memberships later.
- Usage/billing ingress:
  - `POST /usage` (auth + tenant match) to record per-tenant usage metrics (provider/model/tokens/cost/metrics map).
  - `GET /usage?surface=...&window_days=...` to read recent usage for dashboards/temperature.
- Temperature metric sourcing: `TemperatureService` uses a pluggable metrics adapter:
  - Default: in-memory adapter aggregates `UsageRepository`.
  - Reserved: external adapter can pull from a metrics provider keyed by `metrics_primary` slot (stubbed for now).

### Auth examples (dev)
- Signup:
```
curl -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"me@example.com","password":"pw1234","tenant_name":"Acme"}'
```
- Login:
```
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"me@example.com","password":"pw1234"}' | jq -r .access_token)
```
- Call protected keys route:
```
curl -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-Id: t_acme" -H "X-Env: dev" \
  http://localhost:8000/tenants/t_acme/keys
```
- Analytics config (effective read):
```
curl -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-Id: t_acme" -H "X-Env: dev" \
  "http://localhost:8000/tenants/t_acme/analytics/config/current?env=dev&surface=squared"
```

## Persistence config
- Identity repository: in-memory by default; set `IDENTITY_BACKEND=firestore` (requires `GCP_PROJECT` + `google-cloud-firestore`) for users/tenants/memberships.
- Usage repository: in-memory by default; set `USAGE_BACKEND=firestore` for per-tenant usage records.
- Identity repo backends:
  - `IDENTITY_BACKEND=inmemory` (default): all auth/user/tenant ops in-memory for local/dev/tests.
  - `IDENTITY_BACKEND=firestore`: persists to Firestore using ADC credentials. Collections:
    - `identity_users/{user_id}`
    - `identity_tenants/{tenant_id}`
    - `identity_memberships/{membership_id}`
    - `key_configs/{tenant_env_slot}`
    - `analytics_configs/{tenant_env_surface}`
  - Required env: `GCP_PROJECT` or `GCP_PROJECT_ID`. No tenant defaults; all calls must carry tenant/env via RequestContext/JWT.
- Quickstart (dev/in-memory):
  - `uvicorn engines.chat.service.server:app --reload`
  - `curl -X POST http://localhost:8000/auth/signup -H "Content-Type: application/json" -d '{"email":"me@example.com","password":"pw1234","tenant_name":"Acme"}'`
  - `curl -X POST http://localhost:8000/auth/login -H "Content-Type: application/json" -d '{"email":"me@example.com","password":"pw1234"}'`
  - Use returned bearer to hit protected routes (keys, analytics, temperature).
  - Firestore mode behaves the same API-wise; only persistence changes.

## Analytics events guidance
- `DatasetEvent` already carries `utm_*`, `seo_*`, `analytics_event_type`, `analytics_platform`.
- Use `analytics_event_type` values such as `pageview`, `cta_click`, `form_submit`, `email_open`, `email_click`, `app_event`.
- `analytics_platform` should be a short label (e.g., `ga4`, `meta`, `tiktok`, `snap`, `internal`).
- Emit events with `tenant_id/env/user_id` populated; connectors will later read `EffectiveAnalyticsConfig` to route them to GA/Meta/etc.

## Strategy Lock (hard gate)
- Model: `StrategyLock{id, tenant_id, env, surface?, scope, title, description?, constraints{}, allowed_actions[], created_by_user_id, approved_by_user_id?, status(draft|approved|rejected|expired), valid_from, valid_until?, created_at, updated_at}`.
- Repo: in-memory default; Firestore via `STRATEGY_LOCK_BACKEND=firestore`.
- Service: `check_action_allowed(tenant_id, env, surface, action)` → `StrategyDecision{allowed, reason?, lock_id?}`; `require_strategy_lock_or_raise(context, surface, action)` raises 409 with `strategy_lock_required`.
- Routes (`/strategy-locks`): create (draft), list/filter, get, patch (edit), approve/reject (owner/admin only). Tenant + env + JWT enforced.
- Gated actions (Strategy Lock):
  - `temperature:upsert_floors`, `temperature:upsert_ceilings`, `temperature:upsert_weights`
  - `analytics:config_upsert`
  - `kpi:corridor_upsert`
  - `seo_page_config_update`, `builder:update_page`, `builder:publish_page`, `builder:update_global_seo`
  - `vector:ingest`
  - `safety:kill_switch_update`
  - Locks may carry `three_wise_id`; if set, an APPROVE verdict is required in addition to lock approval.
- Example (dev):
```
TOKEN=$(curl -s -X POST http://localhost:8000/auth/signup -H "Content-Type: application/json" -d '{"email":"me@example.com","password":"pw1234","tenant_name":"Acme"}' | jq -r .access_token)
HDRS=(-H "Authorization: Bearer $TOKEN" -H "X-Tenant-Id: t_acme" -H "X-Env: dev")
# Create draft
LOCK_ID=$(curl -s -X POST http://localhost:8000/strategy-locks "${HDRS[@]}" -H "Content-Type: application/json" \
  -d '{"surface":"squared","scope":"kpi_corridor","title":"Allow edits","allowed_actions":["temperature:upsert_floors","analytics:config_upsert"]}' | jq -r .id)
# Approve
curl -X POST http://localhost:8000/strategy-locks/$LOCK_ID/approve "${HDRS[@]}"
# Gated write succeeds
curl -X PUT http://localhost:8000/temperature/floors "${HDRS[@]}" -H "Content-Type: application/json" \
  -d '{"tenant_id":"t_acme","env":"dev","surface":"squared","performance_floors":{"weekly_leads":10}}'
# Without approval, writes return 409 {"error":"strategy_lock_required"}
```

## Firearms (licence gate)
- Actions guarded (requires `require_licence_or_raise`):
  - `dangerous_tool_use` (medium)
  - `agent_autonomy_high` (high)
  - `publish_sensitive` (high)
- Licences are tenant/env scoped with levels (`low|medium|high`); active licence with >= required level allows the action.

## AWS Infra Checks (debug-only)
- Env: `AWS_DEFAULT_REGION` (default `us-east-1`), optional `AWS_PROFILE` (falls back to standard AWS SDK chain).
- Validate locally: `aws sts get-caller-identity`.
- Runtime helpers (no Bedrock/S3/Dynamo yet):
  - `GET /debug/aws-identity` (owner/admin) → STS identity `{account_id, arn, user_id, region}`; fails clearly if creds invalid.
  - `GET /debug/aws-billing-probe` (owner/admin) → minimal Cost Explorer read; returns `ok=false` with missing permission if denied.
  - Budget usage events accept `provider="aws"` and will attach `metadata.aws_account_id` / `metadata.aws_principal_arn` when available.

## Budget / Usage
- Model: `UsageEvent{id, tenant_id, env, surface?, tool_type?, tool_id?, provider, model_or_plan_id?, tokens_input, tokens_output, cost (USD), currency, metadata{}, created_at}`.
- Repo: in-memory default; Firestore via `BUDGET_BACKEND=firestore` (collection `budget_usage/{tenant_env}/events`).
- MAYBES: in-memory default; Firestore via `MAYBES_BACKEND=firestore` (collection tree `maybes/{tenant_env}/items`).
- Analytics events: in-memory default; Firestore via `ANALYTICS_EVENTS_BACKEND=firestore` (collection `analytics_events/{tenant_env}/items`).
- Service: `record_usage`, `query_usage`, `summary(window_days, group_by=provider|model_or_plan_id|tool_type)`.
- Routes under `/budget/usage` (JWT + tenant membership):
  - `POST /budget/usage` (single or list) — records usage for the caller’s tenant/env.
  - `GET /budget/usage` — list recent usage with filters.
  - `GET /budget/usage/summary` — totals + grouped breakdown.

## Cognito Hosted UI (optional)
- Env vars: `COGNITO_REGION`, `COGNITO_USER_POOL_ID`, `COGNITO_APP_CLIENT_ID`, optional `COGNITO_ISSUER` override (otherwise `https://cognito-idp.{region}.amazonaws.com/{userPoolId}`), optional `COGNITO_JWKS_URL` (defaults to issuer `/.well-known/jwks.json`), `COGNITO_TOKEN_USE` (defaults `id`).
- Tokens: accepts Cognito **ID tokens** (RS256) only; JWKS cached for 5 minutes with rotation support. Audience/issuer/token_use/exp enforced.
- Bootstrap: first Cognito login auto-creates user, tenant (slug from email local-part), and owner membership; repeated calls are idempotent. Invite-to-existing-tenant is TODO-stubbed.
- Who am I: `GET /auth/me` or `GET /auth/bootstrap` with `Authorization: Bearer <ID_TOKEN>` returns `{user_id,email,tenant_ids,default_tenant_id,role_map}`.
- Example (after Hosted UI redirect): `curl -H "Authorization: Bearer $ID_TOKEN" -H "X-Tenant-Id: <ignored>" -H "X-Env: dev" http://localhost:8000/auth/me`

## Stripe Billing (skeleton)
- Env vars: `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_<PLANKEY>` (or `STRIPE_PRICE_DEFAULT`), `STRIPE_SUCCESS_URL`, `STRIPE_CANCEL_URL`.
- Routes: `POST /billing/checkout-session` (owner/admin, tenant-scoped) → creates Checkout Session with plan key metadata; `POST /billing/webhook` verifies Stripe signature and updates subscription status (`active|past_due|canceled`); repo tracks `comped` override per tenant.
- Comped: service supports `set_comped(tenant_id, plan_key, comped=True)` to mark free tenants without Stripe.

## Event sinks
- Nexus backend selection via `NEXUS_BACKEND=firestore|bigquery|noop` (default: firestore).
- BigQuery sink configured with `NEXUS_BQ_DATASET` / `NEXUS_BQ_TABLE`; failures should degrade gracefully (no crash).

## Kill switches
- Model: per-tenant/env disablements for providers, autonomy, and specific actions.
- Routes: `GET/PUT /kill-switches` (owner/admin + Strategy Lock action `safety:kill_switch_update`).
- Enforcement: Budget usage blocks disabled providers; action/autonomy checks available via kill switch service helpers.

## Intentionally ungated writes (low-risk)
- Budget usage ingest (`/budget/usage`) — telemetry only.
- MAYBES scratchpad CRUD (`/maybes`) — tenant-scoped notes.
- Memory blackboards/session messages (`/memory`) — tenant-scoped session data.
- Example (dev):
```
curl -X POST http://localhost:8000/budget/usage "${HDRS[@]}" -H "Content-Type: application/json" \
  -d '{"tenant_id":"t_acme","env":"dev","surface":"squared","tool_type":"embedding","tool_id":"vector_explorer","provider":"openai","model_or_plan_id":"gpt-4o","tokens_input":1000,"tokens_output":200,"cost":0.01}'
curl http://localhost:8000/budget/usage/summary "${HDRS[@]}"
```

## KPIs / Corridors
- Models:
  - `KpiDefinition{id, tenant_id, env, surface?, name, description?, unit?, created_at, updated_at}`
  - `KpiCorridor{id, tenant_id, env, surface?, kpi_name, floor?, ceiling?, cadence_floor?, cadence_ceiling?, created_at, updated_at}`
- Repo: in-memory default; Firestore stubbed.
- Routes under `/kpi` (JWT + tenant):
  - `POST /kpi/definitions` — create definition (owner/admin).
  - `GET /kpi/definitions` — list.
  - `PUT /kpi/corridors` — upsert corridor (owner/admin) **gated by Strategy Lock action `kpi:corridor_upsert`**.
  - `GET /kpi/corridors` — list.
- Temperature snapshot now carries `kpi_corridors_used` + `usage_window_days` for downstream analysis.
- Example (dev):
```
# Create + approve strategy lock for KPI updates
LOCK_ID=$(curl -s -X POST http://localhost:8000/strategy-locks "${HDRS[@]}" -H "Content-Type: application/json" \
  -d '{"surface":"squared","scope":"kpi_corridor","title":"Allow KPI","allowed_actions":["kpi:corridor_upsert"]}' | jq -r .id)
curl -X POST http://localhost:8000/strategy-locks/$LOCK_ID/approve "${HDRS[@]}"
# Define KPI and corridor
curl -X POST http://localhost:8000/kpi/definitions "${HDRS[@]}" -H "Content-Type: application/json" \
  -d '{"tenant_id":"t_acme","env":"dev","surface":"squared","name":"weekly_leads","unit":"count"}'
curl -X PUT http://localhost:8000/kpi/corridors "${HDRS[@]}" -H "Content-Type: application/json" \
  -d '{"tenant_id":"t_acme","env":"dev","surface":"squared","kpi_name":"weekly_leads","floor":50,"cadence_floor":3}'
```

## SEO Page Config
- Model: `PageSeoConfig{tenant_id, env, surface, page_type, title, description, og_title?, og_description?, og_image_url?, canonical_url?, timestamps}`.
- Repo: in-memory default; Firestore stub reserved.
- Routes (`/seo/pages`, JWT + tenant):
  - `PUT /seo/pages` — upsert (owner/admin) **gated by Strategy Lock action `seo_page_config_update`**.
  - `GET /seo/pages` — list for tenant/env (optional surface filter).
  - `GET /seo/pages/{surface}/{page_type}` — fetch one.
- Example (with Strategy Lock):
```
LOCK_ID=$(curl -s -X POST http://localhost:8000/strategy-locks "${HDRS[@]}" -H "Content-Type: application/json" \
  -d '{"surface":"squared","scope":"kpi_corridor","title":"Allow SEO","allowed_actions":["seo_page_config_update"]}' | jq -r .id)
curl -X POST http://localhost:8000/strategy-locks/$LOCK_ID/approve "${HDRS[@]}"
curl -X PUT http://localhost:8000/seo/pages "${HDRS[@]}" -H "Content-Type: application/json" \
  -d '{"tenant_id":"t_acme","env":"dev","surface":"squared","page_type":"home","title":"Home","description":"Welcome"}'
```

## Analytics Events (pageview/CTA)
- Models: `PageViewEvent{surface,page_type?,url?,referrer?,utm_*...}` and `CtaClickEvent{surface,page_type?,cta_id?,label?,url?,utm_*...}`.
- Service wraps into `DatasetEvent` with `analytics_event_type` (`pageview` / `cta_click`) and sends to logging engine.
- Routes (`/analytics/events`, JWT + tenant membership):
  - `POST /analytics/events/pageview`
  - `POST /analytics/events/cta-click`
- Example:
```
curl -X POST http://localhost:8000/analytics/events/pageview "${HDRS[@]}" -H "Content-Type: application/json" \
  -d '{"surface":"squared","page_type":"home","url":"https://example.com","utm_source":"newsletter"}'
curl -X POST http://localhost:8000/analytics/events/cta-click "${HDRS[@]}" -H "Content-Type: application/json" \
  -d '{"surface":"squared","page_type":"home","cta_id":"buy_now","label":"Buy Now","url":"https://example.com/checkout"}'
```

## Strategy Lock actions (builder reserved)
- Reserved action names for future builder gating: `builder:publish_page`, `builder:update_page`, `builder:update_global_seo`, `seo_page_config_update`.

## 3-Wise LLM (skeleton)
- Model: `ThreeWiseRecord{id, tenant_id, env, surface?, question, context?, opinions[{model_id, content}], verdict?, metadata{}, created_by, timestamps}`.
- Repo: in-memory default; Firestore via `THREE_WISE_BACKEND=firestore`.
- Routes (`/three-wise`):
  - `POST /three-wise/questions` — submit question (stub opinions/verdict today).
  - `GET /three-wise/questions` — list for tenant/env.
  - `GET /three-wise/questions/{id}` — fetch one.

## Audit logging
- Sensitive actions emit `DatasetEvent` with `analytics_event_type="audit"` (e.g., strategy lock create/approve/reject, key upserts, page create/update/publish/delete).

## Firearms licences (hard gate)
- Model: `FirearmsLicence{id, tenant_id, env, subject_type, subject_id, scope?, level(low|medium|high), status(active|revoked|expired), issued_by, issued_at, expires_at?, metadata{}, timestamps}`.
- Repo: in-memory default; Firestore via `FIREARMS_BACKEND=firestore` (collection `firearms_licences`).
- Routes (`/firearms/licences`, JWT + tenant):
  - `POST /firearms/licences` (owner/admin) — issue.
  - `PATCH /firearms/licences/{id}` (owner/admin) — revoke.
  - `GET /firearms/licences/{id}` — fetch.
  - `GET /firearms/licences` — list with filters.
  - `POST /firearms/licences/dangerous-demo/{subject_type}/{subject_id}` — sample gate for `dangerous_tool_use`.
- Gate helper: `require_licence_or_raise(ctx, subject_type, subject_id, action)`.
- Example:
```
LOCK_HDRS=(-H "Authorization: Bearer $TOKEN" -H "X-Tenant-Id: t_acme" -H "X-Env: dev")
curl -X POST http://localhost:8000/firearms/licences "${LOCK_HDRS[@]}" -H "Content-Type: application/json" \
  -d '{"tenant_id":"t_acme","env":"dev","subject_type":"agent","subject_id":"agent123","level":"medium"}'
curl -X POST http://localhost:8000/firearms/licences/dangerous-demo/agent/agent123 "${LOCK_HDRS[@]}"
```

## Memory (session + blackboard)
- Models:
  - `SessionMemory{id, tenant_id, env, user_id, session_id, messages[{role,content,timestamp,metadata}], metadata{}, ttl_hint?, timestamps}`
  - `Blackboard{id, tenant_id, env, surface?, scope, key, data{}, session_id?, metadata{}, expires_at?, timestamps}`
- Repo: in-memory default; Firestore via `MEMORY_BACKEND=firestore` (collections `memory_sessions`, `memory_blackboards`).
- Routes (`/memory`, JWT + tenant):
  - `POST /memory/session/messages?session_id=...` — append message (uses user_id from JWT).
  - `GET /memory/session/messages?session_id=...` — read session memory.
  - `PUT /memory/blackboards/{key}` — write/update.
  - `GET /memory/blackboards/{key}` — read.
  - `DELETE /memory/blackboards/{key}` — clear.
- Example:
```
curl -X POST "http://localhost:8000/memory/session/messages?session_id=s1" "${LOCK_HDRS[@]}" -H "Content-Type: application/json" \
  -d '{"role":"user","content":"hi"}'
curl "http://localhost:8000/memory/blackboards/k1" "${LOCK_HDRS[@]}"
```
