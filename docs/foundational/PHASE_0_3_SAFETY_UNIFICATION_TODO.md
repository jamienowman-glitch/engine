# Phase 0.3 — Safety Unification TODO (Docs-Only)

Executive summary: we are wiring existing safety subsystems (GateChain, Strategy Lock, 3-wise, KPI, Budget, Temperature/Selecta, Firearms, Kill Switch) into real user paths (chat + canvas) with durable replay and persisted policy. No rebuilds, no refactors, no env-driven policy. All work lands on main.

## Lane Plan (checkboxes)
- [ ] TODO-0.1 (Coordination): Review/approve scope; confirm gating action names (chat_send, canvas_command, canvas_gesture, tool_exec) and target surfaces. Acceptance: written ack with names/surfaces.

- [ ] TODO-1.1 (RequestContext + X-Mode enforcement)  
  - Files: engines/common/identity.py (RequestContext, get_request_context); engines/chat/service/ws_transport.py (_resolve_hello_context/_context_from_scope).  
  - Patch sketch: add mode Literal["saas","enterprise","lab"]; require X-Mode; flag/remove X-Env fallback (temporary warning with TODO removal). WS hello validates mode or rejects.  
  - Acceptance: `curl -X POST /api/auth/ticket` without X-Mode → 400 invalid mode; WS hello without mode → close code 4003.  
  - Commit msg: `engines: enforce X-Mode in RequestContext`

- [ ] TODO-2.1 (GateChain on chat HTTP send)  
  - File: engines/chat/service/http_transport.py::post_message.  
  - Patch sketch: gate_chain.run(ctx, action="chat_send", surface=ctx.surface_id or "chat", subject_type="thread", subject_id=thread_id); SAFETY_DECISION on pass/block.  
  - Acceptance: POST chat message blocked when policy missing; passes when policy present.

- [ ] TODO-2.2 (GateChain on chat WS send)  
  - File: engines/chat/service/ws_transport.py::websocket_endpoint.  
  - Patch sketch: gate_chain.run(ctx, action="chat_send", surface=ctx.surface_id or "chat", subject_type="thread", subject_id=thread_id); on block, close with reason and emit SAFETY_DECISION.

- [ ] TODO-2.3 (GateChain on canvas command/gesture)  
  - Files: engines/canvas_stream/service.py::publish_canvas_event, publish_gesture.  
  - Patch sketch: gate_chain.run(ctx, action="canvas_command"/"canvas_gesture", surface=ctx.surface_id or "canvas", subject_type="canvas", subject_id=canvas_id); emit SAFETY_DECISION.  
  - Commit msg: `engines: GateChain on chat and canvas actions`

- [ ] TODO-3.1 (Canvas timeline replay)  
  - Files: engines/canvas_stream/service.py publish_canvas_event/publish_gesture; engines/realtime/timeline.py if needed.  
  - Acceptance: restart server; reconnect SSE with Last-Event-ID → prior canvas events replayed.

- [ ] TODO-3.2 (SAFETY_DECISION events)  
  - Files: engines/nexus/hardening/gate_chain.py::_emit_audit; engines/chat/service/transport_layer.py::publish_message; canvas_stream/service.py.  
  - Patch sketch: define StreamEvent SAFETY_DECISION (action, result, reason, gate); append to timeline_id (thread_id/canvas_id) and log via emit_audit_event on pass/block.  
  - Acceptance: safety block returns 403 and SAFETY_DECISION appears in timeline replay.  
  - Commit msg: `engines: safety decisions appended to timeline and canvas replay`

- [ ] TODO-4.1 (Budget policy model + repo)  
  - Files: engines/budget/repository.py; engines/budget/models.py (BudgetPolicy with tenant/env/surface/mode/app/threshold).

- [ ] TODO-4.2 (Budget policy API + GateChain)  
  - Files: engines/budget/routes.py (/budget/policy GET/PUT); engines/nexus/hardening/gate_chain.py::_enforce_budget.  
  - Patch sketch: GateChain reads policy from repo; 403 budget_threshold_missing if none; env vars ignored.  
  - Acceptance: PUT /budget/policy sets threshold; GateChain blocks when usage > threshold; env vars ignored.  
  - Commit msg: `engines: persisted budget policy and gate enforcement`

- [ ] Lane 5 (UI) + Lane 6 (Agents): tracked here only; implemented in their repos later.

## Acceptance Checks (global)
- Chat: Sending message triggers GateChain; if blocked (e.g., budget exceeded), SAFETY_DECISION appended to thread timeline and appears in replay/UI reason.
- Canvas: Command/gesture events appended to timeline; after restart, SSE with Last-Event-ID replays events; safety blocks produce SAFETY_DECISION.
- Budget: Threshold set via persisted policy API; GateChain blocks on exceed; env vars ignored.
- Headers: X-Mode required across HTTP/WS/SSE; requests without mode rejected.

## Do NOT Do
- No env-driven safety policy (budget thresholds must not read env).  
- No branches; main only.  
- No refactors/rebuilds of existing safety systems.  
- No code changes outside the specified files; no UI/Agents edits in this repo.

## Parallelization Plan (high level)
- Lane 0: prerequisite for naming/coordination.  
- Lane 1 (RequestContext/mode) must land before GateChain/testing.  
- Lane 4 (budget policy persistence) should land before GateChain budget checks.  
- Lane 2 and Lane 3 can proceed once Lane 1 is in; GateChain budget enforcement depends on Lane 4 to drop env thresholds.  
- UI/Agents (Lane 5/6) proceed in parallel after Engine surfaces are stable.
