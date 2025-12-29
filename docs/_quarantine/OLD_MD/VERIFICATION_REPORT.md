# 88mph Verification Report

## Phase 1 — PII & GDPR primitive
- Implementation: `engines/guardrails/pii_text/engine.py` + `schemas.py` (email/phone/card/postal detection + masking); `engines/logging/events/engine.py` (PII strip + `train_ok` calculation); `engines/privacy/train_prefs.py` (tenant/user opt-out); `engines/dataset/events/schemas.py`; audit helper `engines/logging/audit.py`.
- Routes/entrypoints: logging pipeline used by chat (`engines/chat/pipeline.py`), analytics events (`engines/analytics_events/routes.py`), reactive content, vector ingest loggers, and audit emitters.
- Env/config: `NEXUS_BACKEND` selects sink (default Firestore), `TENANT_ID` / `ENV` for event metadata; optional `NEXUS_BQ_DATASET` / `NEXUS_BQ_TABLE` when BigQuery is chosen.
- Tests run: `python3 -m pytest engines/guardrails/pii_text/tests engines/logging/events/tests` (pass).
- Expected runtime behavior: combined text from input/output/metadata is masked where PII detected; `pii_flags` and policy reason persisted on DatasetEvent; `train_ok` reflects PII policy AND tenant/user opt-out (no impact on runtime responses); events written to configured Nexus backend and echoed to stdout for auditability.
- Gaps: allowlist/mode fields on request are unused; audit logger defaults to no-op unless explicitly set by caller.

## Phase 2 — Event sink to BigQuery
- Implementation: backend selector `engines/nexus/backends/__init__.py`; Firestore sink `firestore_backend.py`; BigQuery sink `bigquery_backend.py` (adds `ingested_at`); logging pipeline hooks via `engines/logging/events/engine.py` and `engines/logging/event_log.py`.
- Routes/entrypoints: any DatasetEvent emission path (chat logger, analytics events, reactive content, Nexus ingest) flows through the backend selector.
- Env/config: `NEXUS_BACKEND` (`firestore|bigquery|noop`), `NEXUS_BQ_DATASET`, `NEXUS_BQ_TABLE`, `GCP_PROJECT`/`GCP_PROJECT_ID` for Firestore, `ENV`/`APP_ENV` for snapshots.
- Tests run: `python3 -m pytest engines/nexus/tests engines/nexus/backends/tests` (pass). Fixed test blocker by allowing `VertexVectorStore` to accept injected index/endpoint ids and error clearly when missing; behavior unchanged for selecta-driven config.
- Expected runtime behavior: events persist to Firestore collections (`nexus_events_{tenant}`) by default; when `NEXUS_BACKEND=bigquery`, events are inserted into the configured dataset/table with UTC `ingested_at` and errors are surfaced in the return payload without crashing callers.
- Gaps: no documented/tabled partitioning strategy or index guidance for BigQuery; dataset/table naming conventions not recorded in this folder.

## Phase 3 — COGS: AWS + GCP
- Implementation: budget ingestion + summaries in `engines/budget/service.py` and `repository.py`; cost estimator + credit priors in `engines/budget/cogs.py`; AWS identity/billing probe in `engines/common/aws_runtime.py`; debug routes `engines/debug/aws_routes.py`; Bossman COGS exposure in `engines/bossman/routes.py`; budget routes `engines/budget/routes.py`.
- Routes/entrypoints: `/budget/usage` POST/GET/summary; `/debug/aws-identity`, `/debug/aws-billing-probe`; Bossman `/bossman/tenant-dashboard` returns `cogs`.
- Env/config: `BUDGET_BACKEND` (`firestore` optional), `AWS_DEFAULT_REGION`/`AWS_PROFILE` (AWS SDK), `AUTH_JWT_SIGNING` for auth in tests, tenant/env headers required on routes.
- Tests run: `python3 -m pytest engines/budget/tests tests/test_aws_runtime.py tests/test_aws_routes.py` (pass; AWS runtime tests skipped when boto3 absent).
- Expected runtime behavior: budget records enforce kill-switch provider blocks and attach AWS identity metadata when provider="aws"; summaries windowed by days with group-by provider/model/tool; `CostEstimator` adds priors per provider and GCP token price lookup; Bossman surfaces provider/model summaries plus credit remaining; AWS debug routes require owner/admin and return 200 with `ok` flag even on access-denied to avoid failing health.
- Gaps: Azure support is placeholder (no live estimator, only a stub entry); COGS freshness/source metadata not explicit in responses; GCP costing limited to one price table entry and no live billing probe.

## Phase 4 — Bossman UI backend readiness
- Implementation: `/bossman/tenant-dashboard` in `engines/bossman/routes.py` aggregates temperature snapshots/config, budget summaries, COGS estimator output, KPI definitions/corridors, strategy locks (active + recent), firearms licences, analytics configs/SEO, event sink backend info, training preferences, and kill-switch snapshot.
- Routes/entrypoints: `GET /bossman/tenant-dashboard?surface={}&window_days={}` (FastAPI router with tenant prefix).
- Env/config: depends on underlying services (`NEXUS_BACKEND` for sink display, budget backend, strategy/firearms backends, kill switch backend); JWT auth required with tenant membership + owner/admin role.
- Tests run: `python3 -m pytest tests/test_bossman_dashboard.py` (pass).
- Expected runtime behavior: owner/admin receives tenant/env-scoped dashboard; windowing applies to budget/temperature summaries; surface defaults to `squared`; lists are capped (temperature snapshots limit=5, recent locks top 10) to avoid payload blowups.
- Gaps: freshness timestamps are implicit (e.g., budget/COGS summaries lack explicit generated_at); event_sink `last_write_at` is always `None` (no health check); pagination for KPIs/firearms/etc. is not parameterized beyond the baked-in limits.

## Phase 5 — Safety sweep completion
- Implementation: Strategy Lock enforcement via `get_strategy_lock_service().require_strategy_lock_or_raise` on temperature upserts (`engines/temperature/routes.py`), analytics config upsert (`engines/identity/routes_analytics.py`), KPI corridor upsert (`engines/kpi/routes.py`), SEO page upsert (`engines/seo/routes.py`), vector ingest (`engines/nexus/vector_explorer/ingest_routes.py`), kill-switch update (`engines/kill_switch/routes.py`); Firearms gating + licence issuance in `engines/firearms/service.py` and `routes.py`; gate matrix and intentionally-ungated list documented in `docs/infra/AUTH_TENANT_SPINE_DEV_RUN.md`.
- Routes/entrypoints: `/strategy-locks` CRUD/approve/reject; `/firearms/licences` CRUD + dangerous-demo gate; gated write routes above enforce membership + owner/admin role and Strategy Lock where specified.
- Env/config: `STRATEGY_LOCK_BACKEND`, `FIREARMS_BACKEND`, `AUTH_JWT_SIGNING` for JWT dev mode; tenant/env headers mandatory on gated routes.
- Tests run: `python3 -m pytest engines/firearms/tests engines/kill_switch/tests` (pass; Firestore firearms repo test skipped without flag).
- Expected runtime behavior: state-changing writes return 409 `strategy_lock_required` unless an approved lock covers the action (Three-Wise verdict checked when lock carries an id); dangerous actions require active firearms licence at or above required level; intentionally ungated telemetry routes remain open but tenant-scoped as documented.
- Gaps: Three-Wise remains stubbed (no real verdicting beyond stored record); kill-switch action/autonomy gates exist in service but are not wired into most action paths (only provider block is actively enforced via budget usage).

## Phase 6 — “What’s running” / kill switches
- Implementation: kill-switch models/repo/service in `engines/kill_switch/*`; endpoints `/kill-switches` (GET/PUT) with owner/admin + Strategy Lock action `safety:kill_switch_update`; provider kill-switch enforcement in `engines/budget/service.py`; Bossman dashboard includes kill-switch snapshot.
- Routes/entrypoints: `/kill-switches` (tenant-scoped); provider enforcement triggered whenever budget usage is recorded; autonomy/action helpers available in service for callers.
- Env/config: Firestore-backed repo auto-selected when available; requires `GCP_PROJECT` for Firestore, otherwise in-memory; JWT + tenant headers required on routes.
- Tests run: `python3 -m pytest engines/kill_switch/tests` (pass) — included in Phase 5 run above.
- Expected runtime behavior: tenants can disable providers (blocks budget recording) and set `disable_autonomy`/`disabled_actions` flags stored per tenant/env; reads/writes require approved strategy lock and owner/admin role; Bossman surfaces current switch state.
- Gaps: no endpoint aggregates “what’s running” (workers/jobs/background spenders) beyond existing per-engine job routes; `disable_autonomy` and `disabled_actions` are not consumed by runtime services, so automation/agent flows are not actually halted yet.

## Smoke commands (dev/local examples)
```
# Bossman dashboard (requires bearer with tenant membership + owner/admin)
curl -H "Authorization: Bearer $TOKEN" -H "X-Tenant-Id: t_demo" -H "X-Env: dev" \
  "http://localhost:8000/bossman/tenant-dashboard?surface=squared&window_days=7"

# Kill switch read/update (strategy lock required for PUT)
curl -H "Authorization: Bearer $TOKEN" -H "X-Tenant-Id: t_demo" -H "X-Env: dev" \
  http://localhost:8000/kill-switches
curl -X PUT -H "Authorization: Bearer $TOKEN" -H "X-Tenant-Id: t_demo" -H "X-Env: dev" \
  -H "Content-Type: application/json" \
  -d '{"disable_providers":["aws"],"disable_autonomy":true}' \
  http://localhost:8000/kill-switches

# AWS debug probes (owner/admin)
curl -H "Authorization: Bearer $TOKEN" -H "X-Tenant-Id: t_demo" -H "X-Env: dev" \
  http://localhost:8000/debug/aws-identity
curl -H "Authorization: Bearer $TOKEN" -H "X-Tenant-Id: t_demo" -H "X-Env: dev" \
  http://localhost:8000/debug/aws-billing-probe
```
