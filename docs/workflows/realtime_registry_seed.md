# Realtime Registry Seeding

Registry writes are required before streaming transports will allow tenants to access threads/canvases. Use `engines.realtime.isolation.register_thread_resource` and `register_canvas_resource` (or the Firestore-backed registry directly) from the Nexus-facing mutation workflows so that a tenant’s resources are known ahead of time.

## Recommended flow

1. When a tenant creates a new chat thread or canvas via Nexus, call the registry helper with the canonical tenant/env + resource ID before returning the identifier to the client.
2. Streaming transports (`/ws/chat/{thread_id}`, `/sse/chat/{thread_id}`) continue to call `verify_thread_access`; if the registry entry is missing they log the `unknown thread` warning and return 404.
3. Firestore-backed registry documents live in the `realtime_registry` collection with documents named `thread__{thread_id}` or `canvas__{canvas_id}` and contain `{ "tenant_id": "..."} `. Admin scripts can pre-populate these entries for migrations or cross-products.

Seeding docs like this ensures that even durable deployments enforce tenant isolation without relying on process-local state.
