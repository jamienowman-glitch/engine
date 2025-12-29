# PHASE 8 — Session Memory Placeholder

> [!NOTE]
> **DONE**: Implemented `SessionTurn` and `SessionSnapshot` models with `SessionMemoryService`. Uses in-memory storage (list per session) with strict tenancy.

Goal:
- Minimal per-user/session memory primitive with tenant/env scoping, TTL, and opt-out tags; no reasoning.

In-scope (engines only):
- Memory record: tenant_id, env, user_id, session_id, message_summary_refs (card refs or separate store), pii_flags, train_ok, created_at, expires_at.
- Routes: `POST /memory/session-snapshot`, `GET /memory/session/{session_id}`; role: tenant member.
- Retention TTL defaults and config; deletion/expiry enforcement; DatasetEvents for writes/reads with tenant/env/user/trace.
- Storage can reuse cards or dedicated store; must remain opaque to engines (no interpretation).

Out-of-scope:
- LLM summarization, conversational reasoning, retrieval orchestration.
- Cross-session or cross-user sharing.

Affected engine modules:
- `engines/memory` (or `engines/nexus/memory`), `engines/logging/events`, `engines/identity/auth`, `engines/config`.

Runtime guarantees added:
- Memory records are tenant/env/user scoped; TTL enforced; opt-out respected via train_ok=false.
- Missing context fails closed; no memory content leaked across tenants/users.

What coding agents will implement later:
- Build models/routes/storage with TTL handling; add tests for isolation, TTL expiry, opt-out flags.
- Add DatasetEvent logging for snapshot create/read; config validation for retention.

How we know it’s production-ready:
- Tests show TTL deletion/expiry works; tenant/user isolation enforced; opt-out flags persisted.
- Snapshot creation/read emits audit logs; absence of auth/context blocks access.
