

⸻

Phase 1 Logs / Audit / Trace — Definition of Done (v0)

Scope

Build an audit-grade, flow-grade logging spine that:
	•	lets you debug agent/flow behavior as a story
	•	meets enterprise accountability
	•	supports streaming + replay
	•	is PII-safe by design
	•	is ready to plug into safety + memory next

Non-goals (Phase 1):
	•	Implementing safety policy logic (that’s Phase 2)
	•	Implementing memory blackboards/scratchpads/agents memory (that’s Phase 3)
	•	UI features beyond consuming streams (UI should “bend” to this logging contract)

⸻

1) Canonical Event Contract

Done when: there is exactly one canonical event envelope used everywhere (dataset events, audit events, stream events all map to it cleanly), and every event is queryable by the core scope keys.

Required fields on every event
	•	tenant_id
	•	env
	•	project_id
	•	surface_id
	•	app_id
	•	user_id (or actor_user_id if human)
	•	request_id (generated if missing)
	•	trace_id and span_id (at least trace_id)
	•	run_id (flow run / session)
	•	step_id (node/step in the flow)
	•	event_id (unique, sortable)
	•	event_type (enumerated)
	•	actor_type: agent | human | system | tool
	•	actor_id (agent id / user id / system)
	•	timestamp + optional duration_ms
	•	severity: debug | info | warn | error
	•	schema_version
	•	pii_policy flags (ex: contains_pii=false, redacted=true, train_ok=true/false)
	•	storage_class: ops | audit | stream | cost (one event can write to multiple sinks)

Rule: no component is allowed to emit “freeform logs only” for critical behavior; it must emit events using this contract (dev logs still exist, but they aren’t the system of record).

⸻

2) Event Types You Must Support

Done when: these exist and are emitted end-to-end with consistent IDs.

A) Flow + agent behavior timeline (“story mode”)
	•	flow_started, flow_ended
	•	step_started, step_ended
	•	agent_message (sanitized summary; no chain-of-thought dumping)
	•	agent_decision (why a branch/tool/plan was chosen — short explanation)
	•	framework_bridge (CrewAI/AutoGen/LangGraph/etc. normalized into same timeline)

B) Shared-state “pulse” events (NOT called blackboard)

(We’ll reserve blackboard for memory phase.)
	•	state_pulse with:
	•	keys changed (or key diff summaries)
	•	counts (items in pile)
	•	optional hash of full state for integrity (“pile stopped growing” becomes obvious)

C) Tool / model call accountability
	•	tool_call_started, tool_call_ended, tool_call_failed
	•	include tool name, provider, and a redacted input/output summary
	•	include model id when applicable (model_id, provider, region)

D) Safety + HITL path capture (even before full safety exists)
	•	safety_gate_evaluated, safety_escalated, safety_decision
	•	human_prompted, human_approved, human_rejected

E) Cost + usage
	•	usage_recorded containing token counts + estimated/actual cost fields
	•	must link to tenant_id/run_id/step_id/model_id/tool_id

F) Errors
	•	exception_raised (stack trace allowed in ops store, but PII-handled)
	•	invariant_failed (contract broken, missing context, mismatch, etc.)

⸻

3) Storage & Immutability

Done when:
	•	Events are written to durable infra by default (no silent in-memory default outside tests).
	•	There is a clear split between:
	1.	Ops timeline store (fast query, debugging)
	2.	Audit store (append-only, tamper-evident)

Audit-grade requirement (minimum viable)
	•	Append-only semantics: no update/delete of audit events.
	•	Tamper-evidence: per-tenant (or per-run) hash chaining:
	•	each audit event stores prev_hash and hash(event_payload + prev_hash)
	•	Query by: tenant/env/project/user/surface/app/run/step/time range.

⸻

4) PII Boundary & Redaction

This is the “don’t ever regret it later” part.

Done when:
	•	Nothing containing PII crosses the LLM boundary.
	•	Every tool/model call event stores:
	•	a redacted payload (always)
	•	optionally an encrypted tenant-owned payload (for rehydration), if you want that capability

Requirements
	•	A single PII redaction layer exists and is used for:
	•	logging
	•	tool calls
	•	LLM calls
	•	Rehydration rules are explicit:
	•	what can be reinserted
	•	for which tenant/user permissions
	•	and where that mapping lives (later memory phase can improve it, but Phase 1 must not block it)

⸻

5) Streaming + Replay (UI-ready contract without building UI)

Done when:
	•	SSE/WS can emit a selective stream of events (not everything).
	•	Replay works from a durable store, not only in-memory.
	•	Client can resume via cursor (Last-Event-ID or resume_cursor) and receive consistent ordering.

Minimum semantics:
	•	at-least-once delivery + idempotent event IDs
	•	replay window configurable per tenant/app

⸻

6) Retention / DSAR / Export

Done when:
	•	You can configure retention by tenant (at least policy object exists, even if defaults are simple).
	•	You can export a run or tenant slice.
	•	You can delete where required (GDPR/DSAR), with the deletion itself being auditable.

⸻

7) Developer Logs (classic)

Done when:
	•	Standard Python logs remain available, but:
	•	they are structured JSON
	•	always include request_id, trace_id, tenant_id, project_id
	•	exception logs correlate back to timeline/audit events

⸻

8) Phase 1 Acceptance Gates

Phase 1 is “done” only if these gates pass (they can be tests + static inspection + a short runtime smoke):
	1.	Event contract gate: every mounted router emits canonical envelope events for request start/end and errors.
	2.	Context gate: project/surface/app are present on emitted events for any request that has RequestContext.
	3.	PII gate: prove PII redaction is applied before LLM/tool boundary + before persistence.
	4.	Audit gate: tamper-evident chaining verified for a sample run.
	5.	Streaming gate: resume/replay returns the same ordered events for a run.
	6.	Usage gate: token/cost usage event emitted and queryable by tenant/run.
	7.	Retention gate: retention/export/delete endpoints or commands exist and are auditable.

⸻
