# PHASE 3 — Cards (YAML Header + NL Body)

> [!NOTE]
> **DONE**: Implemented `Card` model, `parse_card` logic, `CardService`, and routes. Format `YAML --- NL` validated.

Goal:
- Store and retrieve cards as “YAML header + NL body” with versioning, tenant/env scoping, and light validation only.

In-scope (engines only):
- Card model: card_id, tenant_id, env, card_type, version, artifact_refs, created_at, created_by, pii_flags, train_ok, body_text (raw text) and parsed header/nl.
- Parser `parse_card(text)` returning `{header_dict, nl_body}`; require minimal keys, allow unknown keys; reject malformed YAML.
- Routes: `POST /nexus/cards` (create), `GET /nexus/cards/{card_id}`, `POST /nexus/cards/{card_id}/revisions` (versioned create).
- Storage: Firestore (or equivalent) for metadata/text; DatasetEvents for create/read with tenant/env/user/trace.
- Strategy Lock gating on strategic card types where required; role enforcement owner/admin for writes.

Out-of-scope:
- Engine-side interpretation, ranking, or orchestration using card content.
- Embedding/indexing (handled in later phase).

Affected engine modules:
- `engines/nexus/cards` (new), `engines/logging/events`, `engines/identity/auth`, `engines/config/runtime_config`.

Runtime guarantees added:
- Card writes/reads require tenant/env/auth; stored payload includes tenant/env; revisions keep lineage/version refs.
- PII flags/train_ok stored and logged; no card content leaked across tenants.
- Parser is deterministic; failures return clear errors without partial writes.

What coding agents will implement later:
- Build parser/models/routes; add unit tests for YAML parsing (valid/invalid/unknown keys), versioning, and tenant isolation.
- Add DatasetEvent emission for create/read/revision; config validation for storage backends.

How we know it’s production-ready:
- Tests prove parsing correctness and tenant/env isolation; revisions retrievable in order.
- Creating and retrieving a sample “surface KPI spec” card works deterministically; missing tenant/env/auth fails closed.
