# PHASE 5 — Influence Packs

> [!NOTE]
> **DONE**: Implemented `InfluencePack` model, `PackService` (wrapping `CardIndexService`), and `POST /nexus/influence-pack`.
> **Correction**: Confirmed packs are strictly containers of *references* (IDs, scores, opaque excerpts). No semantic interpretation or body generation in engine.

Goal:
- Deterministic influence packs bundling retrieved cards with provenance for downstream agents, without engine-side interpretation.

In-scope (engines only):
- InfluencePack model: id, tenant_id, env, created_at, created_by, query, filters, list of CardRef (card_id, rank, excerpt, artifact refs), optional NL summary (empty allowed).
- Route: `POST /nexus/influence-pack` (takes query + filters, returns pack with ranked cards + excerpts).
- Logging: DatasetEvent capturing query, filters, pack id, card refs, counts, tenant/env/user/trace.
- Deterministic excerpting (e.g., first N chars or YAML field) without semantic alteration.

Out-of-scope:
- LLM summarization, ranking heuristics beyond vector/filters, or orchestration responses.
- New card semantics or behavior changes.

Affected engine modules:
- `engines/nexus/packs` (service/routes), `engines/nexus/index` for retrieval, `engines/logging/events`, `engines/identity/auth`.

Runtime guarantees added:
- Pack creation is tenant/env scoped; returns only same-tenant cards; user context logged.
- Missing index config blocks pack creation with explicit error; no silent fallbacks.

What coding agents will implement later:
- Build pack service/route using existing search; add deterministic excerpting; add tests for tenant isolation and determinism with stub index.
- Emit DatasetEvents for pack creation; add validation for required query/filters fields.

How we know it’s production-ready:
- Tests show deterministic pack output for fixed index stub; cross-tenant access blocked.
- Pack creation returns card refs with provenance and emits audit logs; errors surfaced when search/index config absent.
