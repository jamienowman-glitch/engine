# PHASE 02 — PII + GDPR + Audit

Goal:
- PII-safe ingestion/logging/export with tenant/user/env scoping; audit trails emit DatasetEvents with redaction flags and opt-out state.

Entry conditions:
- Canonical DatasetEvent schema exists (`engines/dataset/events/schemas.py`) and PII filter helpers exist in logging/privacy modules.
- Nexus backends accept DatasetEvents (Firestore/BigQuery) and PII flags.

In-scope (engines only):
- Enforce PII redaction before persistence/logging across chat, media, analytics_events, nexus ingest, vector explorer ingest, budget usage, and auth flows.
- Carry `pii_flags`, `train_ok`, `tenant_id`, `env`, `user_id`, `trace_id/request_id` on all DatasetEvents and audit entries.
- Define retention/erasure hooks for tenant/user data in storage/Nexus/vector metadata paths (contract only).
- Validate env var/secret presence for PII filters; fail closed when missing.

Out-of-scope:
- New privacy policy semantics or user consent UX; no LLM-based PII detection changes beyond validation.
- Moving cards/prompts into engines.

Affected engine modules:
- `engines/logging/events`, `engines/logging/audit`, `engines/dataset/events`, `engines/privacy`, `engines/media`, `engines/chat/pipeline`, `engines/analytics_events`, `engines/nexus/backends`, `engines/nexus/vector_explorer`.

Runtime guarantees added:
- All persisted events/artifacts include tenant/env/user plus redaction markers; PII never stored raw in Nexus/vector/Storage without redaction tag.
- Audit DatasetEvents emitted for sensitive actions (strategy_lock, key handling, temperature/kpi edits) with tenant/env/user/trace.
- Export paths honor `train_ok=false` and tenant/user erasure.

What coding agents will implement later:
- Wire PII filter middleware into all logging pipelines; add schema validators for PII fields.
- Add erasure/retention tests for Nexus docs, vector metadata, and storage objects keyed by tenant/env/user.
- Add audit logging hooks for sensitive routes; unit/integration tests proving redaction happens.

How we know it’s production-ready:
- Tests show PII fields are redacted/masked before persistence and exports.
- Audit DatasetEvents exist for sensitive routes with correct tenant/env/user and trace ids.
- Erasure/retention procedures documented and tested per tenant/user.
