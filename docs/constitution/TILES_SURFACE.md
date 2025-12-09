# TILES SURFACE – CONTRACT (PLANNING)

Planning-only contract for CEO Tiles surfaced at OS level. No engines or runtime code are defined here.

## Goals
- LLM “CEO agent” composes a ranked tile list using Nexus + feeds; no tile-scoring engine.
- Cross-surface mix: always include at least one KPI tile, one deep content tile (long-read/video/podcast), and one strategy/next-step tile.
- Tiles align with manifest/token graph and cluster capabilities; tiles carry content refs, not style mutations.

## Tile registry (types)
- Registry will live alongside this doc (JSON or table) with `type` codes, `display_name`, `kind` (`kpi|content|action|strategy|reactive`), and expected payload fields.
- Allowed starter types (extendable): `content.youtube_video`, `content.long_read`, `content.podcast`, `content.reactive`, `kpi.content`, `kpi.crm`, `kpi.ecom`, `strategy.next_step`, `strategy.lock_pending`, `action.prompt_to_publish`.
- Size hints: `S|M|L|XL`; visual weight only (tight masonry). No layout gaps implied.
- Tiles never mutate tokens; they reference content/metrics only.

## Tile payload (conceptual)
```json
{
  "tile_id": "tile_123",
  "type": "content.youtube_video",
  "size_hint": "M",
  "title": "Top performer this week",
  "summary": "Video driving 12% uplift WoW",
  "cta_label": "Open in YouTube",
  "cta_ref": { "kind": "external", "url": "https://youtube.com/..." },
  "thumb": "https://...",
  "nexus_refs": ["snip_abc", "event_def"],
  "external_refs": ["yt:video:123"],
  "strategy_lock_state": "pending",
  "actions": [
    { "label": "Promote", "action_ref": "action://ads/promote_video", "autonomy_required": true }
  ],
  "pinned": false,
  "order": 3,
  "timestamps": { "produced_at": "ISO8601", "source_updated_at": "ISO8601" },
  "metadata": { "tenant_id": "t_dev", "env": "dev", "surface": "home", "origin": "ceo_agent", "trace_id": "trace_123" }
}
```
- `tile_id` stable per composition; `order` is the rank in the returned list.
- `cta_ref` prefers refs (`nexus://...`) over raw URLs; `cta_url` allowed when refs unavailable.
- `nexus_refs` preferred for provenance; `external_refs` used until ingested.
- `strategy_lock_state`: `pending|allowed|blocked|not_required`; optional `icon` and `reason`.
- `actions` present only when Strategy Lock/3-Wise/HITL allow auto-action; otherwise suppressed or marked pending.

## Content + manifest alignment
- Tiles reference existing content/snippets/events; they do not carry manifest token mutations.
- Size hints inform UI weight; layout decisions stay in the manifest/token graph.
- Tiles can reference manifest slots or surfaces via metadata but never write to them directly.

## CEO agent contract (planning)
- Inputs: tenant/env, requested limit, optional filters, contextual signals (recent DatasetEvents, external feeds), and Strategy Lock context.
- Outputs: ordered list of tiles (payload above) plus rationale/trace id for audit.
- The CEO cluster composes payloads only; it does not mutate manifest tokens or bypass capabilities.

## Strategy Lock
- Tiles carry lock state; auto-actions present only when pre-cleared by Strategy Lock (and 3-Wise if required).
- Pending/blocked states should render lock icon hints; actions suppressed or marked pending.
- Lock state TTL is short-lived; UI must revalidate before executing any action and refresh state on reconnect.
- Actions scoped per tile; no inherited permissions across tiles even if action_ref is similar.

## Mix guidance
- At least one KPI tile, one deep content tile (long read/video/podcast), and one strategy/next-step tile per composition when available.
- Respect tenant/env filters and pinning; pinned tiles can hold fixed `order` slots or float within a band as defined by UI.

## Extensibility
- Tile `type` is open-ended; registry will live in PLAN-0AD.
- Additional fields can be added if they do not violate manifest/token graph separation.

## Non-goals (this doc)
- No HTTP/WS implementation.
- No scoring algorithms or LLM prompts; only the payload contract and behaviours.
