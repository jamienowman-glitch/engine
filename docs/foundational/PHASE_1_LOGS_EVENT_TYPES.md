# Phase 1 Logs — Event Types & Required Fields

## Canonical envelope (apply to all event types)
- Required: tenant_id, env, project_id, surface_id, app_id, user_id/actor_id, actor_type, request_id, trace_id, run_id, step_id, event_id (sortable), event_type (enum), timestamp, severity, schema_version, storage_class (ops|audit|stream|cost), pii_policy flags.  
  Evidence of current gaps: engines/dataset/events/schemas.py:9-32 (missing project/app/run/step/severity/schema_version); engines/realtime/contracts.py:19-165 (routing lacks project/app, has event_id/meta.persist); engines/common/identity.py:22-151 (RequestContext supplies scope keys).

## Event type set
- Flow timeline: flow_started, flow_ended, step_started, step_ended, agent_message, agent_decision, framework_bridge.  
- State pulse: state_pulse (key diffs + hash + counts).  
- Tool/model accountability: tool_call_started, tool_call_ended, tool_call_failed (provider, model_id, redacted payload, cost hooks).  
- Safety/HITL: safety_gate_evaluated, safety_escalated, safety_decision, human_prompted, human_approved, human_rejected.  
- Cost/usage: usage_recorded (tokens/cost/model/tool/run/step).  
- Errors: exception_raised, invariant_failed.  
- Streaming envelope: StreamEvent maps to event_id/type/meta.persist (engines/realtime/contracts.py:74-165).  
- Audit: audit_action (hash chained) derived from emit_audit_event (engines/logging/audit.py:18-53).
