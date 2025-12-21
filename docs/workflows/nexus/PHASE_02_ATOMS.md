# PHASE 2 — Atoms (Derived Artifacts)

> [!NOTE]
> **DONE**: Implemented `AtomArtifact`, `InMemoryAtomRepository`, `AtomService`, and routes. Deterministic pipeline established.

Goal:
- Deterministic raw → atom pipeline with lineage, coordinates, and tenant/env-scoped metadata storage.

In-scope (engines only):
- `AtomArtifact` model: artifact_id, tenant_id, env, parent_asset_id, uri, source_start_ms?, source_end_ms?, op_type, op_version, captured_at, derived_at, capture_location?, location_confidence?.
- `AtomRepository` (Firestore acceptable) storing metadata with tenant/env keys.
- One deterministic atomizer path (e.g., text paragraph splitter or video frame grab) that uses no LLMs; writes atom metadata.
- Route: `POST /nexus/atoms/from-raw` invoking atomizer, persisting metadata, emitting DatasetEvents.
- Enforce lineage: atom links to parent asset; pii_flags/train_ok propagated; Strategy Lock gating if atom definitions change.

Out-of-scope:
- Semantic interpretation, embeddings, ranking, or card logic.
- Multi-step workflows/orchestration.

Affected engine modules:
- `engines/nexus/atoms` (new), deterministic engine helper (e.g., `engines/text` or `engines/media` minimal), `engines/logging/events`, `engines/identity/auth`.

Runtime guarantees added:
- Atom creation requires tenant/env/auth; repository keys by tenant/env; cross-tenant access blocked.
- Deterministic outputs stable given same input; lineage stored and logged.
- DatasetEvents emitted for atom creation with tenant/env/user/trace and refs to raw asset/atom ids.

What coding agents will implement later:
- Build models/repos/route; implement deterministic atomizer with tests for stability; add isolation tests for tenant/env.
- Add validation that parent asset exists and belongs to same tenant/env.

How we know it’s production-ready:
- End-to-end test shows raw asset → atom creation → metadata retrieval with consistent coordinates and lineage.
- Cross-tenant access attempts fail; missing parent asset fails cleanly with audit log.
