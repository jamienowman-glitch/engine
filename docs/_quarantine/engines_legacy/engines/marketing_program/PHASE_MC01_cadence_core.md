# PHASE_MC01_cadence_core

## 1. North star + Definition of Done  
- North star: A reusable cadence core that manages content pools and assets across channels/types, enforces pool-level and per-asset cooldowns, and can suggest candidate slots for a date range deterministically.  
- Definition of Done:  
  - Models for content pools (content_type, pool_id, tags, min_days_between_repeats, anchor_channel? optional) and assets (asset_id, content_type, channels, pool_id, per-asset cooldown, tags/meta).  
  - Service can, given date range + pools + assets + rules, produce candidate slots per channel/type respecting pool and asset cooldowns; deterministic outputs for identical inputs.  
  - API endpoints to register/list pools/assets and to request a schedule suggestion (read-only generation).  
  - Basic conflict detection (cooldown violations) surfaced in responses; no writes to external systems.  
  - Built-in defaults for cooldowns/caps by content_type (stories, short_form, long_form, email/dm flows, email/dm broadcasts, feed/carousels/community, blog/homepage) and global daily caps (target 5–7/day, hard cap 10/day) plus per-channel caps; defaults are configurable later but wired now.  
  - Integration point defined for emitting timeline_core-compatible tasks/lanes/tags (shape documented, implementation may be stubbed with deterministic payload).  
  - Tests cover validation, cooldown enforcement, determinism, and conflict reporting.

## 2. Scope (In / Out)  
- In: engines/marketing_cadence models/service/routes/tests, docs for this phase.  
- Out: No auth/tenant/RequestContext changes; no connectors/UI/orchestration; no logging/memory pipelines; no external pushes to channels.  

## 3. Modules to touch (hard allow-list)  
- engines/marketing_cadence/models.py  
- engines/marketing_cadence/service.py  
- engines/marketing_cadence/routes.py  
- engines/marketing_cadence/tests/test_models.py  
- engines/marketing_cadence/tests/test_service.py  
- engines/marketing_cadence/tests/test_routes.py  
- docs/engines/marketing_program/PHASE_MC01_cadence_core.md  
- docs/engines/marketing_program/MC_CRITICAL_TODOS.md  
> STOP RULE: If you believe any file outside this list must be changed to complete this phase, stop and return a report instead of editing it.

## 4. Implementation checklist (mechanical)  
- Define Pydantic models: ContentPool, CadenceAsset, CooldownRule (pool-level min_days_between_repeats, asset-level cooldown_days), ChannelType/ContentType enums, ScheduleRequest (date range, channels/types, pools/assets refs, request_id, tenant/env), ScheduleSuggestion (slots, conflicts, meta).  
- Encode default caps/cooldowns per content_type/pool:  
  - stories: target 3/day anchor, hard cap 5/day/channel; pool cooldown 3d; asset cooldown 28–30d.  
  - short_form (incl trial/experimental): target 1–2/day/channel (soft), hard cap 3/day/channel; pool cooldown 14d (trial may ignore pool cooldown if underfilling day), asset cooldown 90d.  
  - long_form: no auto repeats by default (one-shot unless explicitly allowed).  
  - email/dm flows: min gap 1d between steps; max 1 flow email and 1 flow dm per user per day (expressed as channel/type cap).  
  - email broadcasts: max 3/week/segment; dm broadcasts: max 2/week/segment.  
  - feed/carousel/community: target 1/day/channel, hard cap 2/day/channel; pool cooldown 7d; asset cooldown 60d.  
  - blog: no repeats by default; homepage hero: asset cooldown 14d.  
  - Global caps: comfort target 5–7/day total; hard cap 10/day; enforce per-channel caps first, then global; drop/push lower-priority items if caps exceeded.  
- Implement pool/asset repositories (in-memory) in service; CRUD for pools/assets via routes; validation for tenant/env present.  
- Implement scheduling function: given pools/assets and date range, propose slots per channel/type using round-robin across pools while respecting pool cooldown and asset cooldown; deterministic ordering (e.g., sort inputs, stable assignment).  
- Implement conflict detection: mark where cooldown would be violated; include in response.  
- Add timeline_core adapter stub: shape tasks/lanes/tags payload (no external calls) with deterministic ids/hashes from inputs.  
- Keep all behavior inside allow-listed files; if more needed, STOP.  

## 5. Tests  
- test_models.py: validate enums, required fields, cooldown rule validation, deterministic hash/id helpers if present.  
- test_service.py: schedule generation respects pool and asset cooldowns, deterministic outputs for same inputs, conflict reporting, timeline adapter shape contains expected lanes/tags.  
- test_routes.py: CRUD pools/assets, schedule endpoint validates tenant/env and returns expected structure; 4xx on bad inputs.  
Tests run:  
- `python3 -m pytest engines/marketing_cadence/tests/test_models.py`  
- `python3 -m pytest engines/marketing_cadence/tests/test_service.py`  
- `python3 -m pytest engines/marketing_cadence/tests/test_routes.py`

## 6. Docs & examples  
- Include example JSON: define pools (brand_story, testimonials) with min_days_between_repeats, assets with per-asset cooldown; request to fill next 14 days; sample response with slots per channel/type and conflicts.  
- Document default caps/cooldowns (above) as applied if request does not override; show example of target vs hard cap handling.  
- Document timeline adapter shape (task id/hash, lane=channel, tag=content_type/pool) and show a stub example.

### Example: MC01 Full Workflow

#### 1. Define Content Pools

```json
POST /cadence/pools
{
  "pool_id": "pool_brand_stories_001",
  "tenant_id": "tenant_acme",
  "env": "prod",
  "content_type": "stories",
  "channels": ["instagram", "facebook"],
  "min_days_between_repeats": 3,
  "tags": ["brand", "seasonal"]
}
```

#### 2. Register Assets to Pool

```json
POST /cadence/assets
{
  "asset_id": "story_asset_001",
  "tenant_id": "tenant_acme",
  "env": "prod",
  "content_type": "stories",
  "pool_id": "pool_brand_stories_001",
  "channels": ["instagram"],
  "cooldown_days": 28,
  "tags": ["winter_collection"]
}
```

#### 3. Request 14-Day Schedule

```json
POST /cadence/generate-schedule
{
  "request_id": "req_jan_2025_001",
  "tenant_id": "tenant_acme",
  "env": "prod",
  "start_date": "2025-01-01",
  "end_date": "2025-01-14",
  "pool_ids": ["pool_brand_stories_001"],
  "asset_ids": ["story_asset_001"],
  "channels": ["instagram"],
  "content_types": ["stories"],
  "global_daily_cap_soft": 7,
  "global_daily_cap_hard": 10
}
```

#### 4. Response with Slots + Conflicts + Timeline Shape

```json
{
  "request_id": "req_jan_2025_001",
  "tenant_id": "tenant_acme",
  "env": "prod",
  "slots": [
    {
      "slot_id": "5f4d8a2c1b9e3f7a",
      "asset_id": "story_asset_001",
      "pool_id": "pool_brand_stories_001",
      "content_type": "stories",
      "channel": "instagram",
      "scheduled_date": "2025-01-01",
      "priority": 0,
      "tags": {},
      "meta": {}
    },
    {
      "slot_id": "7a3c2f1e9d8b4a6c",
      "asset_id": "story_asset_001",
      "pool_id": "pool_brand_stories_001",
      "content_type": "stories",
      "channel": "instagram",
      "scheduled_date": "2025-01-05",
      "priority": 0,
      "tags": {},
      "meta": {}
    }
  ],
  "conflicts": [
    {
      "conflict_type": "cooldown_violation",
      "asset_id": "story_asset_001",
      "channel": "instagram",
      "scheduled_date": "2025-01-02",
      "message": "Asset story_asset_001 cooldown 28d violated within request (last 1d ago at 2025-01-01)",
      "severity": "warning"
    }
  ],
  "timeline_tasks": [
    {
      "id": "task_abc123def456",
      "tenant_id": "tenant_acme",
      "env": "prod",
      "request_id": "req_jan_2025_001",
      "title": "stories on instagram",
      "start_date": "2025-01-01",
      "lane": "instagram",
      "tags": ["stories", "pool_brand_stories_001"],
      "source_id": "story_asset_001",
      "meta": {
        "asset_id": "story_asset_001",
        "pool_id": "pool_brand_stories_001",
        "content_type": "stories",
        "channel": "instagram"
      }
    }
  ],
  "total_slots": 2,
  "date_range_start": "2025-01-01",
  "date_range_end": "2025-01-14",
  "meta": {
    "global_daily_cap_soft": 7,
    "global_daily_cap_hard": 10
  }
}
```

Notes:
- **Determinism**: Same request inputs always produce same slot IDs and timeline task IDs (hash based).
- **Conflict Reporting**: Conflicts due to cooldowns are surfaced but do not block other valid slots.
- **Timeline Shape**: `lane` maps to channel, `tags` include content_type and pool_id for later filtering in timeline_core.
- **Default Caps Applied**: Stories default to 3/day target (soft) / 5/day hard per channel; pool cooldown 3d applied.



## 7. Guardrails  
- Do not touch auth/tenant/RequestContext code.  
- Do not touch /ui, /core, /tunes.  
- Do not modify connectors, orchestration flows, manifests, or Nexus/agent behaviour.  
- Do not add/change vector store / memory / logging pipelines.  
- Stay within allow-list; STOP on expansion.  

## 8. Execution note  
Workers must implement code+tests+docs strictly within the allow-list to meet DoD. If any work appears to require files outside the list, STOP and report. When all checklist items and tests are satisfied, MC01 is DONE; later phases can extend without breaking these contracts.
