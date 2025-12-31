# Phase 0.3 — Safety Unification Acceptance (Docs-Only)

## Verification script list
1) Headers/mode enforcement  
   - `curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:8000/api/auth/ticket -H "Authorization: Bearer dev" -H "Content-Type: application/json" -d '{"tenant_id":"t_system","project_id":"p_dev","request_id":"req"}'` → expect **400** (missing X-Mode).  
   - Repeat with `-H "X-Mode: lab"` → expect **200**.

2) Budget policy (persisted)  
   - `curl -X PUT http://localhost:8000/budget/policy -H "Authorization: Bearer dev" -H "Content-Type: application/json" -H "X-Mode: lab" -H "X-Tenant-Id: t_system" -H "X-Project-Id: p_dev" -d '{"surface":"chat","threshold":10.0}'` → expect **200**.  
   - Post usage above threshold, then send chat → expect **403** with reason `budget_threshold_exceeded`.

3) Chat GateChain + SAFETY_DECISION  
   - Send chat message via HTTP/WS with headers (X-Mode, X-Tenant-Id, X-Project-Id, X-Request-Id). If blocked, response **403** with reason; timeline for thread contains `SAFETY_DECISION` event (action=chat_send, result=BLOCK/ PASS).  
   - Replay: connect SSE/WS with `Last-Event-ID` to the thread, expect SAFETY_DECISION appears in stream.

4) Canvas replay + GateChain  
   - Issue canvas command/gesture (headers include X-Mode, X-Tenant-Id, X-Project-Id, X-Request-Id). If blocked, response **403** with reason.  
   - Restart server; reconnect to `/sse/canvas/{id}` with `Last-Event-ID` → previously emitted canvas events and SAFETY_DECISION entries replay in order.

5) WS hello contract  
   - Connect WS without mode in hello.context → server closes with code 4003.  
   - Connect with mode=lab → handshake succeeds.

## Expected failure payloads (403)
- JSON body includes `error` field and `gate` reason (e.g., budget_threshold_exceeded, kpi_threshold_missing, temperature_breach, firearms_licence_required, strategy_lock_required, three_wise_verdict_required, kill_switch_blocked).  
- SAFETY_DECISION event mirrors the block with fields: `type: "SAFETY_DECISION"`, `action`, `result` (PASS|BLOCK), `reason`, `gate`.

## SAFETY_DECISION replay definition
- Emitted whenever GateChain evaluates (pass or block).  
- Appended to timeline_id = thread_id for chat, canvas_id for canvas.  
- Fields required: action_name, result PASS|BLOCK, reason_code, gate (budget/kpi/temperature/firearms/kill_switch/strategy_lock/three_wise).  
- Must appear in SSE/WS replay when reconnecting with `Last-Event-ID`.
