# TILES WIRING (PLANNING)

Contracts-only wiring for the CEO Tiles surface. No runtime code is defined here.

## API surface (conceptual)
- HTTP: `GET /tiles?tenant={}&env={}&surface={optional}&limit={optional}&cursor={optional}`
- Optional WS/SSE channel: stream tile updates; same payload shape as HTTP.
- Auth: requires tenant-scoped credentials; no anonymous access.
- Response: ordered list of tile payloads per PLAN-0AD schema, plus cursor if paginated.
- Headers: `If-None-Match`/`ETag` optional for caching; `X-Trace-Id` propagated.
- Query params:
  - `tenant` (required), `env` (required), `surface` (optional), `limit` (default 12, max 20), `cursor` (optional), `types` (comma list).
- Response body:
```json
{
  "tiles": [ /* PLAN-0AD payloads */ ],
  "cursor": "abc123",
  "trace_id": "trace_123",
  "rationale": "Mix selected based on KPI + recent events"
}
```
- Errors: 401 for missing auth, 403 for tenant mismatch, 429 rate limits, 5xx for backend issues.
- Caching: short TTL/ETag allowed; must revalidate strategy_lock_state for actions at execution time.

## Request/response contract (CEO agent)
- Request to CEO orchestrator:
```json
{
  "tenant_id": "t_dev",
  "env": "dev",
  "surface": "home",
  "limit": 12,
  "filters": { "types": ["kpi.content", "content.youtube_video"] },
  "context": { "recent_events": ["content.published.youtube_video"], "audience": "prospects" }
}
```
- Response:
```json
{
  "tiles": [ /* PLAN-0AD payloads */ ],
  "trace_id": "trace_123",
  "rationale": "Prioritised KPI + recent video",
  "next_cursor": null
}
```
- CEO agent must respect cluster capabilities (compose only) and never write manifest tokens.

## Data flow
- Inputs: Nexus snippets/events (Firestore), external feeds, Strategy Lock/3-Wise status, manifest context for surface if needed.
- CEO agent reads inputs, composes ranked tiles, writes composition trace (DatasetEvent `tiles.composed`) and returns payload.
- UI requests tiles via API; no surface grouping in the first view—mix is cross-surface by design.
- Impressions/clicks/actions emit DatasetEvents (`tile.impression`, `tile.action`) with tile_id/type/order/strategy_lock_state/action_ref.
- DatasetEvent shapes (conceptual):
```json
// tiles.composed
{ "kind": "tiles.composed", "tenant_id": "t_dev", "env": "dev", "surface": "home", "trace_id": "trace_123", "count": 12, "pinned": 2, "tiles": [{ "tile_id": "tile_1", "type": "kpi.content", "order": 1, "strategy_lock_state": "allowed" }] }
// tile.impression
{ "kind": "tile.impression", "tenant_id": "t_dev", "env": "dev", "tile_id": "tile_1", "type": "kpi.content", "order": 1, "strategy_lock_state": "allowed", "pinned": false, "timestamp": "ISO8601" }
// tile.action
{ "kind": "tile.action", "tenant_id": "t_dev", "env": "dev", "tile_id": "tile_1", "action_ref": "action://ads/promote_video", "strategy_lock_state": "allowed", "autonomy_required": true, "result": "accepted|blocked|pending_revalidation", "timestamp": "ISO8601" }
```
- Logs exclude PII; action events must revalidate Strategy Lock/3-Wise/HITL at execution time.

## Strategy Lock integration
- Tile payload includes `strategy_lock_state` and optional `actions` only when pre-cleared.
- Planning-only: no new guardrail engines; reuse existing Strategy Lock classification.
- Server caches `strategy_lock_state` per tile for short TTL; must revalidate before executing actions.

## Alignment with manifest/token graph
- Tiles do not mutate tokens; they reference content via Nexus/external refs.
- Cluster capabilities: CEO cluster allowed to compose tile payloads; UI clusters consume; no manifest writes here.

## Triggers / cadence
- Default trigger: pull on demand via API/WS; optional scheduled recompositions (e.g., hourly) and reactive triggers (DatasetEvents).
- WS/SSE channel can push updates when a new `tiles.composed` event arrives for tenant/env/surface.
- Max tile count per response: start with `limit<=20`; server-side cap to prevent overload.

## Open questions to resolve before implementation
- Pagination vs cursor streaming defaults; cache/ETag policy.
- TTL for `strategy_lock_state` caching and revalidation behaviour.
- Rationale retention: how long to keep rationale/trace linked to tiles for audit.
- Retention/sampling for impression/action events; whether to downsample at scale.
