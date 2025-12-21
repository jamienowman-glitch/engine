# PHASE 04 — Nexus Primitives

Goal:
- Harden Nexus as neutral plumbing for raw artifacts → atoms → storage → retrieval with tenant/env scoping and lineage logging only.

Entry conditions:
- Nexus schemas/backends exist (Firestore/BigQuery), RAG/vector interfaces present, Nexus usage logging available.
- Env config exposes `NEXUS_BACKEND` and required dataset/table/index vars.

In-scope (engines only):
- Enforce Nexus stance: raw artifact storage, atom lineage tracking, vector index read/write primitives, logging of card/atom access; zero semantic interpretation, ranking, or card logic.
- Validate tenant/env/kind/space tagging on all NexusDocument/Usage writes; reject missing or mismatched context.
- Make configs explicit + versioned for Nexus backends; fail closed on missing indexes/buckets/secrets.
- Improve observability: DatasetEvents for ingest/query, audit trails of what cards/atoms were accessed, explainability for “why retrieval returned X” via metadata only.
- Add Strategy Lock gating for Nexus definition/index changes where applicable.

Out-of-scope:
- Prompt engineering, card manifests, or orchestrator behaviors inside engines.
- Changing retrieval meaning or ranking semantics.

Affected engine modules:
- `engines/nexus/*` (schemas, backends, rag_service, vector_store), `engines/nexus/logging`, `engines/nexus/tests`, `engines/chat` ingestion hooks, `engines/media` ingestion, `engines/config` for Nexus env.

Runtime guarantees added:
- Every Nexus write/read is tenant/env scoped; backends and vector stores key by `(tenant_id, env)`.
- Backends emit DatasetEvents with tenant/env/user/trace and source refs; errors surfaced, not hidden.
- Config validation prevents starting without Nexus backend/index ids; no default fallbacks that skip scoping.

What coding agents will implement later:
- Add validators around Nexus configs; tighten schemas/metadata/lineage fields.
- Add audit/logging hooks for card/atom access (IDs + timestamps only).
- Add isolation/validation tests for ingest/query per tenant/env/kind.

How we know it’s production-ready:
- Nexus ingest/query fails safely when tenant/env/index config is absent; logs describe missing config.
- Tests prove tenant A cannot read/write tenant B artifacts or usage.
- Lineage and access logs exist for atoms/cards without storing card content in engines.
