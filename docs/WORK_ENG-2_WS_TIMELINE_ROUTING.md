# Worklog: ENG-2 WS Timeline Routing Hardening

## Failure behavior
- `GET /ws/chat/{thread_id}` now catches missing `event_stream` routing, sends `{ "error": { "code": "event_stream.missing_route", "message": "<details>", "http_status": 503, "resource_kind": "event_stream", "details": {} } }`, then closes with WebSocket code 4003.
- Invalid cursor flow continues to emit the `chat.cursor_invalid` / 410 envelope before closing 4003.

## How to reproduce
1. Register a thread for the tenant via `engines.realtime.isolation.registry`.
2. Force `engines.realtime.timeline.get_timeline_store()` to raise `RuntimeError` (e.g., no routing route configured for `event_stream`).
3. Connect to `/ws/chat/{thread_id}` with a valid JWT bearer token.
4. Send the initial `{"type":"hello",...}` payload; the server now emits the missing-route envelope and tears down the socket with close code 4003.

## Tests
- `python3 -m pytest engines/chat/tests/test_ws_timeline_routing.py`

## Files touched
- `engines/chat/service/ws_transport.py`
- `engines/chat/tests/test_ws_timeline_routing.py`
- `docs/WORK_ENG-2_WS_TIMELINE_ROUTING.md`
