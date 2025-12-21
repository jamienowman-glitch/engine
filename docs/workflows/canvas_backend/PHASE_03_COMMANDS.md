# PHASE 03 — Command + Revision Apply (Minimum Viable)

Goal: FE can send atomic edits with base_rev and receive deterministic head or stable REV_MISMATCH for recovery. No CRDT needed; enforce envelopes, tenancy, and revision tracking.

In-scope
- Command endpoint with base_rev, correlation_id, idempotency key, op batch, routing keys, actor id/type.
- Persistent revision head per canvas/project.
- Deterministic apply skeleton + validation hook points (no token/CRDT logic).

Out-of-scope
- Deep CRDT/OT or schema-specific validation.
- UI or orchestration prompts.

Allowed modules to change
- New module for canvas commands (e.g., `engines/canvas_commands/*`) with FastAPI router.
- Persistence using existing backends: Firestore (via Nexus backend or dedicated collection) or in-memory fallback.
- `engines/common/identity.py` (if helpers needed for routing key validation).
- Tests under `engines/canvas_commands/tests`.

Steps
1) Define revision model: {tenant_id, env, workspace_id, project_id, canvas_id, head_rev, updated_at, meta}. Store with Firestore when available, else in-memory.
2) Command endpoint:
   - Input: base_rev (required), idempotency_key, correlation_id, ops[], routing keys, actor id/type.
   - Behavior: if base_rev != head -> return 409 REV_MISMATCH with current head + optional recent ops; else append ops, increment rev, persist head + log DatasetEvent (metadata only).
   - Enforce RequestContext + auth + routing key match.
3) Validation hooks: placeholder callable for op validation; deterministic ordering of ops for replay.
4) Tests:
   - Happy path increments rev and returns new head.
   - Mismatch returns 409 with recovery payload.
   - Idempotency returns same head for duplicate key.
   - Tenant isolation (different tenant cannot mutate/read others).
5) Stop conditions:
   - DO NOT continue if rev storage cannot persist per canvas.
   - DO NOT continue if 409 payload is unstable or missing head info.

Do not touch
- No CRDT/OT merging; no render/timeline/media logic changes; no FE changes.
