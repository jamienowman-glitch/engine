# PHASE 04 — Artifact Store + Nexus Persistence (Drafts)

Goal: Store preview, replay, and audit artifacts for canvas/graft. Binaries go to existing storage (S3 via `RAW_BUCKET` by default, local fallback); metadata/lineage goes to Nexus. Provide minimal fetch endpoints.

In-scope
- Preview artifact (snapshot/render-ref) and replay artifact (keyframes/event summary) plus audit placeholder.
- Binary storage via existing media_v2 S3 path (`RAW_BUCKET` + `boto3`, local fallback); metadata via Nexus backend and media_v2 artifact records.
- Routing keys + tenant/env enforcement.

Out-of-scope
- Publish/export hardening; complex lineage graphs; UI.

Allowed modules to change
- `engines/media_v2/*` (routes/service/models) to enforce RequestContext/auth and allow new artifact kinds if needed.
- `engines/nexus/backends/*` usage for metadata writes (NexusDocument/DatasetEvent).
- New lightweight router for canvas artifacts if media_v2 routes stay generic.
- Tests under `engines/media_v2/tests` or new canvas artifact tests.

Steps
1) Storage choice: reuse media_v2 upload/register to S3 (`RAW_BUCKET`) with local fallback; ensure RequestContext/auth required on asset/artifact routes (tenant/env match).
2) Define artifact types: preview, replay, audit (reuse media_v2 ArtifactKind or add minimal new kinds).
3) Metadata to Nexus: write NexusDocument or DatasetEvent with lineage {tenant_id, env, workspace_id, project_id, canvas_id, rev, correlation_id, actor_id, artifact_id, uri, kind, timestamps}.
4) Endpoints:
   - Create/fetch preview artifact (binary or URI).
   - Create/fetch replay artifact (JSON keyframes).
   - Audit placeholder creation (structured empty report).
   - All enforce routing keys + auth + tenant match.
5) Tests:
   - Tenant isolation on create/fetch.
   - Artifact metadata persisted to media_v2 + Nexus backend.
   - Replay JSON stored and retrievable.
6) Stop conditions:
   - DO NOT continue if media_v2 still unauthenticated.
   - DO NOT continue if Nexus write fails silently (assert backend writes in tests).

Do not touch
- No render pipeline changes; no FE; no new storage provider beyond existing S3/local fallback.
