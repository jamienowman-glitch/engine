# PHASE 07 — File Explorer Backend + Derived Views Registry

1. Goal
- Provide backend queries to list assets by tenant/app/project and a data-driven registry for derived views (no hardcoded app logic).

2. In scope
- Endpoints to list assets for tenant/env, filter by project/surface/app, and list derivatives for an asset.
- Derived views registry: metadata describing how to group/filter assets (registry stored, not behavior).
- Reuse S3 registry/metadata from Phase 06; no new storage format.

3. Out of scope
- UI rendering.
- Embeddings/vector indexing.
- New env var names.

4. Hard boundaries (DO NOT TOUCH)
- Strategy Lock, Firearms, KPI/Temperature semantics.
- 3D/video/audio engines.
- Prompts/cards/orchestration logic.

5. Affected modules
- engines/storage or engines/nexus/raw_storage registry layer.
- engines/file_explorer/* (if created) for routes/services.
- engines/identity/auth for auth checks.
- engines/logging/events for logging.
- tests under engines/file_explorer/tests/*.

6. API surface / routes
- GET /files (filters: project_id?, surface/app_id?, type?, tag?).
- GET /files/{asset_id}/derivatives.
- GET /files/views (returns derived views registry entries).
- All tenant/env scoped; membership required; owner/admin for registry mutation if any (reads are allowed for members).

7. Data model changes
- AssetView/DerivedView registry entry: id, tenant_id, env, name, filters{}, derived_types[], created_at, updated_at.
- Asset metadata reuse from Phase 06.

8. Security & tenant binding
- require_tenant_membership; enforce tenant/env on all queries; registry entries tenant/env scoped.

9. Safety hooks
- DatasetEvents for queries/registry access optional; audit for registry edits if allowed.

10. Observability
- Metrics/logs for query counts, filter usage; error logs on missing tenant/env or config.

11. Config / env vars
- Reuse existing storage configs; no new env vars; fail if storage backend missing.

12. Tests
- Pytests for list/filter by project/surface, tenant isolation, derivatives lookup, registry retrieval; role checks on registry writes if present.

13. Acceptance criteria
- Can list assets by tenant/app/project; see derivatives; fetch registry entries; no cross-tenant leakage.

14. Smoke commands
- curl -H auth/tenant/env "/files?project_id=...&surface=chat"
