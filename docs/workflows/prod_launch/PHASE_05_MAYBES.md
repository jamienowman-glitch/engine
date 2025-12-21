# PHASE 05 — Maybes Scratchpad + Forward-to-Maybe + Promote Hook

1. Goal
- Provide tenant-scoped Maybes scratchpad to save raw text quickly, forward bundles into Maybes, and expose a promote-to-Nexus hook stub (no behavior/LLM in engines).

2. In scope
- Maybe model storing raw text, timestamps, source refs, tags, pinned flag, tenant_id/env/user_id.
- Endpoints: create/list/get/update/delete Maybes; save message bundle to Maybe; forward-to-Maybe from prior phases.
- Promote hook stub to Nexus (pointer only, no ingestion/LLM in engines).

3. Out of scope
- Changing Maybes semantics to act like Nexus; no summarization or prompts.
- Strategy Lock/Firearms semantics changes.
- New env var names.

4. Hard boundaries (DO NOT TOUCH)
- 3D/video/audio engines.
- KPI/Temperature/Strategy Lock/Firearms logic.
- Card/prompt logic in engines.

5. Affected modules
- engines/maybes/* (routes/service/repo/models/tests).
- engines/identity/auth (auth checks).
- engines/logging/events (DatasetEvents).
- Optional wiring from engines/memory/message bundle forwarding.

6. API surface / routes
- POST /maybes, GET /maybes, GET /maybes/{id}, PUT /maybes/{id}, DELETE /maybes/{id}.
- POST /maybes/from-bundle (inputs: bundle_id or messages + source refs).
- POST /maybes/{id}/promote (stub: records intent/pointer only).
- All tenant/env/user scoped; membership required; owner/admin for delete/update? (define in doc).

7. Data model changes
- Maybe: id, tenant_id, env, user_id?, text, source_refs[], tags[], pinned, created_at, updated_at, pii_flags?, train_ok.
- PromoteIntent: id, maybe_id, tenant_id, env, status (stub), target_ref? (pointer only).

8. Security & tenant binding
- require_tenant_membership; enforce same tenant/env on all operations; role gates for destructive ops.

9. Safety hooks
- DatasetEvents for create/update/delete/promote with tenant/env/user/trace; no Strategy Lock/Firearms changes unless classify promote as strategic (document).

10. Observability
- Logs/metrics for CRUD and forward-to-maybe; promote intent recorded.

11. Config / env vars
- Reuse existing storage/backend config; no new names; fail if backend missing.

12. Tests
- Pytests for CRUD, forward-to-maybe, tenant/user isolation, role gates, pii_flags/train_ok pass-through.

13. Acceptance criteria
- Can save raw text and bundles into Maybes; retrieve/update/delete within tenant/env; promote stub records intent; no leakage.

14. Smoke commands
- curl -X POST /maybes -H auth/tenant/env -d '{"text":"note","tags":["x"]}'
- curl -X POST /maybes/from-bundle -H auth/tenant/env -d '{"messages":[...],"source_refs":[...]}'
