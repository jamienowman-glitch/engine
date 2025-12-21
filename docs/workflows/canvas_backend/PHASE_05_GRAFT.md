# PHASE 05 — Graft Support: Live Visibility vs Auto-Mode Replay

Goal: Provide gesture/visibility channel for human-on-watch mode and keyframed replay + audit logging for auto mode. Controlled by Tenant-0 flags.

In-scope
- Gesture event envelope + routing over existing rails (WS for live gestures, SSE optional fanout).
- Toggle behavior (log / don’t log / keyframe only) controlled by Tenant-0 feature flags.
- Auto mode: record keyframes + audit log without live fanout.

Out-of-scope
- UI, rendering of gestures, CRDT merge, prompt/persona logic.

Allowed modules to change
- Realtime modules from PHASE 02 (chat WS, canvas SSE, new gesture channel).
- Feature flag storage from PHASE 01.
- Artifact persistence from PHASE 04 (replay artifacts).
- Tests under corresponding realtime/artifact test dirs.

Steps
1) Gesture envelope: {routing keys, actor_id, gesture_kind (caret/selection/drag/token_scrub/timeline_nudge), payload, ts}. Validate against RequestContext tenant/env and routing keys.
2) Live mode: If Tenant-0 flags allow, fan out gestures over WS (primary) and optional SSE; presence/heartbeat already in WS from PHASE 02.
3) Logging modes (Tenant-0 flags): log-all (DatasetEvent + replay artifact), keyframe-only (aggregate gestures to keyframes), no-log (fanout only).
4) Auto mode: skip live fanout; always produce replay artifact + audit log entry for ops; ensure routing keys captured.
5) Tests:
   - Gesture events isolated per tenant/canvas.
   - Flag toggles change logging behavior.
   - Auto mode produces replay artifact even without live connections.
6) Stop conditions:
   - DO NOT continue if gesture events bypass auth/RequestContext.
   - DO NOT continue if logging mode ignores Tenant-0 flags.

Do not touch
- No FE; no LLM/prompt logic; no strategy changes outside gesture rails and logging per flags.
