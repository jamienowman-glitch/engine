# PHASE 04 — Session Memory Store + Message Bundle Forwarding

1. Goal
- Provide user-scoped, tenant/env-bound session memory store with message bundle forwarding between threads/projects without leakage.

2. In scope
- SessionMemory model keyed by tenant_id, env, user_id, surface_id, project_id/thread_id.
- Store preferences, pinned facts, pointers, summaries (no raw PII dumps).
- Message bundle primitive: save last N messages; forward bundle to another thread.
- Forward-to-Maybes hook (hand-off only; no behavior change) for next phase.

3. Out of scope
- LLM summarization/orchestration logic.
- New prompts or behavior changes.
- Strategy Lock/Firearms semantics changes.
- New env var names.

4. Hard boundaries (DO NOT TOUCH)
- 3D/video/audio engines.
- Chat orchestration logic.
- KPI/Temperature semantics; Strategy Lock/Firearms logic.
- Card/prompt logic in engines.

5. Affected modules
- engines/memory/* (or new module) for storage.
- engines/chat/service/* (only for optional routing/mounts; avoid behavior changes).
- engines/identity/auth for auth checks (read-only).
- tests under engines/memory/tests/* and engines/chat/tests if routing touched.

6. API surface / routes
- POST /memory/session (create/update memory snapshot).
- GET /memory/session/{session_id}.
- POST /memory/message-bundle (save/forward bundle; params: source_thread_id, target_thread_id, messages[]).
- All tenant/env/user scoped; membership required.

7. Data model changes
- SessionMemory: id, tenant_id, env, user_id, surface_id, project_id?, thread_id?, preferences{}, pinned_refs[], summary_refs[], created_at, updated_at, expires_at.
- MessageBundle: id, tenant_id, env, user_id, source_thread_id, target_thread_id, messages[], created_at.

8. Security & tenant binding
- require_tenant_membership; user_id match enforced; no cross-tenant/thread mixing.

9. Safety hooks
- Audit DatasetEvents for create/update/forward with tenant/env/user/trace; no Strategy Lock/Firearms changes.

10. Observability
- Logs/metrics for create/read/forward; TTL expiry stats.

11. Config / env vars
- Reuse existing storage config; no new env vars; fail if backend missing.

12. Tests
- Pytests for tenant/user isolation, TTL handling, forward bundle between threads in same tenant/env, rejection across tenants.

13. Acceptance criteria
- Memory snapshots stored/retrieved per user/session; bundles forward between threads in same tenant; no leakage; TTL respected.

14. Smoke commands
- curl -X POST /memory/session -H auth/tenant/env -d '{...}'
- curl -X POST /memory/message-bundle -H auth/tenant/env -d '{"source_thread_id":"...","target_thread_id":"...","messages":[...]}'
