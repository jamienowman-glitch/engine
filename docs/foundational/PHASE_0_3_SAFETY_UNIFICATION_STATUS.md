# Phase 0.3 — Safety Unification Status

## Truth Table (from Phase 0.3 TODO)
- TODO-0.1 Coordination: 🟡 Partial — gating action names acknowledged (chat_send/canvas_command/canvas_gesture/tool_exec) but no explicit written ack in repo.
- TODO-1.1 RequestContext + X-Mode enforcement: ✅ Done — `engines/common/identity.py` requires X-Mode, rejects X-Env; WS contexts use it; commit 1686b03 also added trace/run/step headers (beyond scope).
- TODO-2.1 GateChain on chat HTTP send: ✅ Done — `engines/chat/service/http_transport.py` calls `gate_chain.run(...)` before processing.
- TODO-2.2 GateChain on chat WS send: ✅ Done — `engines/chat/service/ws_transport.py` gates “message” branch and closes on block.
- TODO-2.3 GateChain on canvas command/gesture: ✅ Done — `engines/canvas_stream/service.py` publish_canvas_event/publish_gesture call GateChain.
- TODO-3.1 Canvas timeline replay: 🟡 Partial — timeline append uses `realtime/timeline.py` but requires STREAM_TIMELINE_BACKEND=firestore; replay exists but depends on backend availability.
- TODO-3.2 SAFETY_DECISION events: ✅ Done — GateChain emits SAFETY_DECISION StreamEvent; chat/canvas append to timeline; SAFETY_DECISION appears on block.
- TODO-4.1 Budget policy model + repo: 🟡 Partial — budget repo exists but policy persistence not confirmed; env-gating removal not fully verified.
- TODO-4.2 Budget policy API + GateChain: 🟡 Partial — budget routes exist; GateChain budget enforcement present but depends on repo/policy wiring; env vars still referenced in service defaults.

## Evidence
- RequestContext/X-Mode: `engines/common/identity.py` enforces X-Mode, rejects X-Env. WS hello uses RequestContext via get_request_context. Commit: 1686b03.
- Chat HTTP GateChain: `engines/chat/service/http_transport.py::post_message` gate_chain.run(action="chat_send"...).
- Chat WS GateChain: `engines/chat/service/ws_transport.py::websocket_endpoint` gate_chain.run in message branch; closes 4003 on block.
- Canvas GateChain: `engines/canvas_stream/service.py` publish_canvas_event/publish_gesture call GateChain.
- SAFETY_DECISION: `engines/nexus/hardening/gate_chain.py::_emit_safety_decision` builds StreamEvent and audit; chat/canvas append timeline via publish_message; SAFETY_DECISION emitted on pass/block.
- Timeline replay: `engines/realtime/timeline.py` list_after used in chat WS subscribe; backend requires STREAM_TIMELINE_BACKEND=firestore (no filesystem adapter).
- Budget: `engines/budget/repository.py` and `models.py` contain BudgetPolicy; `engines/budget/routes.py` exposes policy; GateChain `_enforce_budget` in `gate_chain.py`; default repo selection still env-driven; no persistence proof provided.

## Acceptance / Proof Needs
- TODO-0.1: needs explicit coordination note (written ack of action names/surfaces).
- TODO-3.1: needs proof with STREAM_TIMELINE_BACKEND configured (or filesystem adapter) showing SSE/WS replay after restart.
- TODO-4.1/4.2: needs curl/pytest proof that PUT /budget/policy persists and GateChain blocks when exceeded; confirm env vars ignored.

## Gap TODO (PHASE_0_3_1) — minimal deltas only
- Timeline backend fallback: add filesystem adapter or documented setup to satisfy replay without Firestore dependency; acceptance: restart + SSE replay passes.
- Budget persistence proof: add test/curl demonstrating PUT /budget/policy persisted and GateChain blocks when usage > threshold; ensure env thresholds ignored.
- Coordination ack: add brief doc note confirming gating actions/surfaces.
