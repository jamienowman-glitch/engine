# MAYBES scratchpad – dev run notes

Lightweight, non-vector scratchpad for long-form snippets saved from chat/agents. Current implementation is in-memory only (no Firestore/DB yet); meant to lock API/contract for future storage plug-ins.

## Running locally
- Start the FastAPI app (includes MAYBES routes) from repo root:
  ```bash
  uvicorn engines.chat.service.server:app --reload --port 8000
  ```
- Routes live under `/maybes/*` (router is mounted on `/maybes`).

## Curl examples

Create (POST /maybes/items):
```bash
curl -X POST http://localhost:8000/maybes/items \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "t_jay",
    "env": "dev",
    "space": "scratchpad-default",
    "user_id": "u_jay",
    "title": "State of Agents – orchestration",
    "body": "long text snippet here ...",
    "tags": ["orchestration", "agents"],
    "source_type": "agent",
    "source_engine": "chat",
    "source_ref": {"thread_id": "thread_123", "message_id": "msg_456"}
  }'
```

List (GET /maybes/items):
```bash
curl "http://localhost:8000/maybes/items?tenant_id=t_jay&env=dev&space=scratchpad-default&tags_any=agents&limit=50&offset=0"
```

Get one (GET /maybes/items/{id}):
```bash
curl "http://localhost:8000/maybes/items/<ITEM_ID>?tenant_id=t_jay&env=dev"
```

Update (PATCH /maybes/items/{id}):
```bash
curl -X PATCH "http://localhost:8000/maybes/items/<ITEM_ID>?tenant_id=t_jay&env=dev" \
  -H "Content-Type: application/json" \
  -d '{ "title": "Updated title", "body": "edited body …", "tags": ["orchestration", "state"], "pinned": true }'
```

Delete (DELETE /maybes/items/{id}):
```bash
curl -X DELETE "http://localhost:8000/maybes/items/<ITEM_ID>?tenant_id=t_jay&env=dev"
```

## API contract (v1, in-memory only)
- POST `/maybes/items` — body `MaybeCreate`; returns `MaybeItem`.
- GET `/maybes/items` — query `tenant_id`, `env`, optional `space`, `user_id`, `tags_any`, `search_text`, `pinned_only`, `archived`, `limit`, `offset`; returns `{items: [MaybeItem]}`.
- GET `/maybes/items/{id}` — path `id`, query `tenant_id`, `env`; returns `MaybeItem` or 404.
- PATCH `/maybes/items/{id}` — path `id`, query `tenant_id`, `env`, body `MaybeUpdate`; returns `{item: MaybeItem}`.
- DELETE `/maybes/items/{id}` — path `id`, query `tenant_id`, `env`; returns `{status: "deleted"}`.

## Tests
- Run from repo root: `pytest engines/maybes/tests`
