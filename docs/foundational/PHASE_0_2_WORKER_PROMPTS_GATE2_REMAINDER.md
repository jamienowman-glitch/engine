# Gate2 Worker Prompts (AuditChain / UsageComplete / HAZEAlign)

## Prompt 1 — AuditChain enforcement
Scope: /Users/jaynowman/dev/northstar-engines (engines/logging/audit.py plus sink).  
Do-not-break: existing audit event API, DatasetEvent schema.  
Tasks: add prev_hash/hash fields to audit emits; ensure writes append-only; propagate storage_class=audit; fail-fast if hash missing.  
DoD: tests/logs/test_audit_hash_chain.py pass; audit sink rejects missing hashes.  
No in-memory/no noop: audit backend must be durable (firestore/bigquery).

## Prompt 2 — UsageComplete (cost kill-switch + /ops/status + Azure stubs)
Scope: /Users/jaynowman/dev/northstar-engines (engines/budget/service/repository, engines/control/ops routes, routing registry entries).  
Do-not-break: budget usage API, kill-switch gating.  
Tasks: ensure UsageEvent includes run_id/step_id/model/tool, storage_class=cost, and persists to durable repo; add /ops/status endpoint hooking to cost rules; add Azure env placeholder entries in multi-cloud routing contract.  
DoD: tests/logs/test_usage_events.py pass; /ops/status returns cost state.  
No in-memory/no noop: budget repo cannot default to InMemory.

## Prompt 3 — HAZEAlign (vector explorer)
Scope: /Users/jaynowman/dev/northstar-engines (engines/nexus/vector_explorer/service.py, ingest_service.py, repository.py, vector_store.py).  
Do-not-break: existing routes and StrategyLock/inject dependencies.  
Tasks: ensure mode headers required; full envelope (mode/project/app/surface/run/step/schema_version/severity/storage_class) on query/scene/ingest events; inject durable logger; apply PII redaction before embeddings; ensure usage events include full context; remove no-op logger fallback.  
DoD: tests/vector_explorer/test_contract_mode.py pass; log records persisted.  
No in-memory/no noop: service must fail-fast without logger/backends.
