# PHASE 03 — Logging + Traceability

Goal:
- Deterministic, tenant-scoped logging and auditability across engines with full traceability (request_id/trace_id) and DatasetEvents as the single ledger.

Entry conditions:
- DatasetEvent schema and logging engine exist; Nexus backends selectable (Firestore/BigQuery).
- Request context carries tenant/env/user and trace metadata.

In-scope (engines only):
- Standardize logging adapters to emit DatasetEvents for all engines (chat, media, vector, budget, KPI/Temperature reads/writes, bossman dashboards, kill_switch/strategy_lock).
- Ensure DatasetEvents include `tenant_id`, `env`, `user_id/auth_subject`, `trace_id/request_id`, `surface`, and source refs; enforce schema validation.
- Add observability hooks: DatasetEvent success/fail metrics, error surfaces, and rate-limit/error codes for key routes.
- Add read-models for UI (dashboard-ready summaries) sourced from logs without new behavior.

Out-of-scope:
- Behavioral orchestration or ranking based on logs; no prompt/agent logic.
- Changing meaning of KPI/Temperature outputs.

Affected engine modules:
- `engines/logging/events`, `engines/logging/event_log`, `engines/logging/audit`, `engines/dataset/events`, `engines/bossman`, `engines/chat`, `engines/media`, `engines/nexus/*`, `engines/budget`, `engines/kpi`, `engines/temperature`.

Runtime guarantees added:
- Every write/read path emits DatasetEvents with tenant/env/user/trace; failures are logged with error codes.
- UI read-models expose per-tenant/env summaries (e.g., recent temperature snapshots, budget summaries) without cross-tenant leakage.
- No DatasetEvent is accepted without tenant/env; missing trace/request ids are synthesized and logged.

What coding agents will implement later:
- Normalize logging helpers; add validation tests for DatasetEvent payloads.
- Add per-feature logging coverage tests (success + failure).
- Add dashboard read-model builders fed only by logs; contract tests for tenant isolation.

How we know it’s production-ready:
- Trace-through tests show a request’s DatasetEvents across services carry consistent tenant/env/user/trace.
- Logs support dashboards without ad hoc queries; metrics show error/success counts per tenant/env.
- No cross-tenant data appears in logs or read-models under concurrent requests.
