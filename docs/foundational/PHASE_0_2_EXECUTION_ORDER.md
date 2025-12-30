# Phase 0→2 Execution Order (Gates 0→3)

## Gate 0 — Storage readiness (GCS pass, S3 blocked)
Rationale: We already proved real persistence on GCS (gs://northstar-os-dev-northstar-raw) with mode=lab key prefix. S3 is kept in-contract but currently blocked by IAM (AccessDenied on PutObject to northstar-dev-boy). Establishes that real infra exists now, so subsequent gates can run against durable storage.

## Gate 1 — Contract foundation (Mode-only, envelopes, no in-memory, PII pre-call)
Rationale: Before replay/memory/audit, we must enforce the core contract: mode replaces env, full event envelopes, ban in-memory/noop defaults, and PII redaction before any LLM/tool/embedding. This prevents further work from depending on legacy env or lossy logging paths.

## Gate 2 — Persistence of streams, memory, audits, usage, HAZE alignment (COMPLETE)
Rationale: Gate 2 deliverables are now merged (memory durable, durable replay, vector-ish ingest/retrieval, cost kill-switch with /ops/status, Azure stubs). Gate 3 can now focus on clients.

## Gate 3 — Client/runtime propagation (agents, UI, connectors)
Rationale: After the engine-side contract is solid, ensure clients (agents/UI/connectors) send mode/tenant/project headers and avoid in-memory assumptions. This is last to avoid rework while the contract stabilizes upstream.
