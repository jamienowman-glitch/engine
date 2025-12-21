# PHASE 4 — Indexing (Vector + Filters over Cards)

> [!NOTE]
> **DONE**: Implemented `CardIndexService` with mock embeddings, `InMemoryVectorStore`, Search API, and integration with `CardService` create flow.

Goal:
- Tenant-scoped card search via vector + filters; indexing on card create/revise with loud failures when config missing.

In-scope (engines only):
- `CardIndexService` to embed header/body and upsert into vector store with metadata filters (tenant_id, env, card_type, timestamps, artifact refs).
- Write path: card create/revision triggers indexing; errors surfaced without silent fallback.
- Read path: `POST /nexus/search` with query text + filters (card_type, time range, artifact type) returning ranked card_ids + snippets + pointers.
- Config validation for vector backend/index ids; observability via DatasetEvents for index + search including tenant/env/user/trace.

Out-of-scope:
- Embedding raw assets; semantic ranking tweaks beyond deterministic adapter behavior.
- Any orchestration decisions based on search results inside engines.

Affected engine modules:
- `engines/nexus/index` (service/routes), `engines/nexus/vector_store` adapters, `engines/nexus/logging`, `engines/identity/auth`, `engines/config`.

Runtime guarantees added:
- Index/search operations require tenant/env/auth; metadata and filters enforce tenant isolation.
- Missing vector config fails closed with clear errors; no default indexes.
- DatasetEvents capture index/search attempts/results with counts and card refs.

What coding agents will implement later:
- Build CardIndexService, routes, and tests for indexing trigger, search filters, tenant isolation; mock embedding/vector backends.
- Add config validators and error pathways; add observability counters/logs.

How we know it’s production-ready:
- Tests show card create triggers index; search returns only same-tenant/env cards; missing config blocks with explicit error.
- Retrieval of known card (“KPI spec”) by NL query succeeds in controlled test.
