# Chat Streaming Hardening (PR-HARD-01 / PR-HARD-02 / PR-STREAM-01)

## Tests
- `python3 -m pytest engines/chat/tests/test_chat_streaming_hardening.py`
- `python3 -m pytest engines/chat/tests/test_ws_hardening.py engines/chat/tests/test_ws_timeline_routing.py`
- `python3 -m pytest engines/chat/service/tests/test_sse_transport.py`

Set `AUTH_JWT_SIGNING`, `ENGINES_TICKET_SECRET`, `ENV`, and routing/timeline backends before running these suites. The new coverage exercises SSE/WS identity rejection, canonical `ErrorEnvelope` responses, cursor validation, and restart-safe replays.

## Manual verification

### SSE (HTTP GET)
1. Create a thread via `engines.realtime.isolation.register_thread_resource("t_demo", "<thread>")` and persist one or more messages through `engines.chat.service.transport_layer.publish_message`.
2. Use a valid JWT (matching `AUTH_JWT_SIGNING`) and call with the required headers:

```bash
curl -N \
  -H "Authorization: Bearer <jwt-token>" \
  -H "X-Tenant-Id: t_demo" \
  -H "X-Mode: lab" \
  -H "X-Project-Id: p_chat" \
  -H "X-App-Id: app-chat" \
  http://localhost:8000/sse/chat/<thread>
```

3. Append `-H "Last-Event-ID:<cursor>"` to resume after a past message; a `resume_cursor` SSE should precede the next `chat_message`.
4. Omit or tamper with any of `X-Mode`, `X-Project-Id`, or `X-App-Id` to confirm the canonical `auth.*_missing` envelope (400) is returned.

### WebSocket (ws://)
1. Connect with `wscat` or similar after registering the thread and writing messages:

```bash
wscat -H "Authorization: Bearer <jwt-token>" -c "ws://localhost:8000/ws/chat/<thread_id>"
```

2. Send the initial `hello` payload:
```json
{
  "type": "hello",
  "context": {
    "tenant_id": "t_demo",
    "mode": "saas",
    "project_id": "p_chat",
    "app_id": "app-chat",
    "user_id": "user-alpha",
    "surface_id": "surface-alpha",
    "request_id": "req"
  }
}
```

3. Add `"last_event_id": "<cursor>"` to restart from a durable timeline (see resume event). Invalid cursors still emit the `chat.cursor_invalid` envelope with HTTP status 410 before closing with code 4003.
4. Use a ticket (`ENGINES_TICKET_SECRET` + `issue_ticket`) with context fields that don’t match the `hello` payload to exercise the `auth.context_mismatch` envelope.
5. Drop any of `mode`, `project_id`, or `app_id` from the `hello` context to confirm `{ "error": { "code": "auth.*_missing", "http_status": 400 } }` plus a 4003 close.

## Notes
- All SSE/WS failures now surface the canonical `ErrorEnvelope` and, for WS, close with WebSocket code 4003 immediately after sending the envelope.
- Replay safety relies on durable `chat_store`/timeline routes; verify the routing registry has a `chat_store` and `event_stream` backend before hitting production modes.
