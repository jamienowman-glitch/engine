# Feature Flags

Tenant-0 owns the global defaults for streaming and control-plane toggles. Each record is scoped to a `(tenant_id, env)` pair and stored durably in Firestore (collection `feature_flags`, document id `tenant_id__env`), with `owner`/`admin` roles allowed to mutate flags for their scope.

## Streaming guarding toggles

- `ws_enabled` – Gate the WebSocket transport. When `false`, live gesture/realtime channels for the tenant env stay disabled unless explicitly overridden by a tenant-level flag.
- `sse_enabled` – Gate Server-Sent Events for telemetry/shadow channels.
- `gesture_logging` – Toggle whether gestures are persisted for replay/audit telemetry.
- `replay_mode` – Controls replay artifact generation (`"off"`, `"keyframe"`, `"stream"`). Tenant-0 defaults determine whether auto replay is sampled or streamed back to clients.
- `visibility_mode` – Controls what clients may do with logged gestures (`"private"`, `"team"`, `"public"`). Defaults come from tenant-0 but tenants can restrict further.

Tenant-specific flags inherit missing values from the corresponding tenant-0 entry, so missing tenant records fall back to the global defaults for their env. Firestore persistence ensures the control-plane can enforce consistent WS/SSE availability and replay behavior even after restarts.
