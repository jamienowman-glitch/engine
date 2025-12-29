# Phase 0→2 Agents Compliance Notes (Mode + No-InMemory)

What must change
- Context propagation: outbound calls must carry X-Mode (saas|enterprise|lab), X-Tenant-Id, X-Project-Id (plus surface/app/user/request as needed). Actor_id/user_id must derive from token when present; no client-invented actor_id.
- Stable run/trace: generate and propagate run_id/trace_id/step_id consistently across nodes/tasks; avoid orphan run_ids. Align with engines’ event envelope (tenant/mode/project/run/step).
- State/memory: remove in-memory/default adapters; use durable storage for any blackboard/session/state. Tests must use isolated durable backends (no noop/memory).
- PII boundary: apply redaction before any LLM/tool/embedding call; log pii_flags/train_ok and support rehydration per tenant policy. Do not store raw prompts unredacted in agent logs/state.
- Audit/usage: emit audit/usage events using canonical envelope (mode/tenant/project/request/trace/run/step) with storage_class (audit/cost). No-op or dropped logs are noncompliant.

Do-not-break
- Atomic cards/graph definitions; maintain import namespace `northstar.*`.
- Existing mode cards/mode loader behavior, but extend to include mode header propagation.

Evidence pointers
- Mode and tenancy fields required by engines RequestContext (engines/common/identity.py:22-151).
- Event envelope gaps (engines/dataset/events/schemas.py:9-32; engines/realtime/contracts.py:74-165) to mirror when emitting from agents.
