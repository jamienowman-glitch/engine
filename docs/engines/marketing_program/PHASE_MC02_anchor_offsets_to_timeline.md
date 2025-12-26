# PHASE_MC02_anchor_offsets_to_timeline

## 1. North star + Definition of Done  
- North star: Multi-channel scheduling that honors anchor platform + offsets per content type, emits a deterministic multi-channel schedule, and maps it into timeline_core-compatible tasks/lanes for Gantt/calendar rendering.  
- Definition of Done:  
  - Models/requests carry anchor_channel per content type and offsets (days) for secondary channels.  
  - Service can take a base cadence (from MC01) and apply offsets to generate per-channel schedules consistently; conflicts surfaced.  
  - Timeline-core adapter produces tasks grouped by channel and content type with stable ids/hashes.  
  - HTTP endpoint to generate offset-applied schedule + timeline payload; deterministic results; tests cover offset math and mapping.  
  - Defaults wired: anchor goes Day 0; example offsets IG:+1, TikTok:+2, stories remix:+0 while respecting per-channel caps/global caps and asset/pool cooldowns inherited from MC01.

## 2. Scope (In / Out)  
- In: Offset logic layered on MC01 schedule; mapping to timeline_core task shape; routes/services/tests/docs for this phase.  
- Out: No new auth/tenant changes; no UI; no connectors/orchestration; no changes to MC01 cooldown logic beyond consuming its output.

## 3. Modules to touch (hard allow-list)  
- engines/marketing_cadence/models.py  
- engines/marketing_cadence/service.py  
- engines/marketing_cadence/routes.py  
- engines/marketing_cadence/tests/test_offsets.py  
- engines/marketing_cadence/tests/test_timeline_mapping.py  
- docs/engines/marketing_program/PHASE_MC02_anchor_offsets_to_timeline.md  
- docs/engines/marketing_program/MC_CRITICAL_TODOS.md  
> STOP RULE: If you believe any file outside this list must be changed to complete this phase, stop and return a report instead of editing it.

## 4. Implementation checklist (mechanical)  
- Extend models to include anchor_channel + offsets per content_type; validate offsets are integers (days) and optional caps for horizon.  
- Implement service function: input = MC01 schedule (base channel), apply offsets to create per-channel entries; ensure deterministic ordering and conflict surfacing (e.g., cooldown violations if offsets collide); apply defaults (Day0 anchor; IG:+1, TikTok:+2, stories:+0) when not overridden.  
- Implement timeline adapter: map offset schedule to timeline_core task shape (lane=channel, tags=content_type/pool), deterministic ids/hashes (e.g., base slot hash + channel + offset).  
- Add route to request offset-applied schedule and return both schedule and timeline payload; validation for tenant/env present; no external calls.  
- Keep changes within allow-list; if more is needed, STOP.  

## 5. Tests  
- test_offsets.py: offset math (positive/zero offsets), deterministic outputs, conflict detection when offsets cause overlaps or cooldown violations, validation of anchor/offset fields.  
- test_timeline_mapping.py: timeline payload grouping by channel/content_type with stable ids/hashes; tasks count matches generated schedule; deterministic ordering.  
Tests run:  
- `python3 -m pytest engines/marketing_cadence/tests/test_offsets.py`  
- `python3 -m pytest engines/marketing_cadence/tests/test_timeline_mapping.py`

## 6. Docs & examples  
- Provide example: anchor=YouTube Shorts for short-form, offsets IG:+1, TikTok:+3 → show base schedule (from MC01) and offset-applied multi-channel schedule + timeline JSON.  
- Mention default offset behavior (Day0 anchor; IG:+1, TikTok:+2, stories:+0) and show how overrides work.  
- Document timeline mapping fields (lane/channel, tags, start_date, meta with anchor/offset).

### Example: MC02 Anchor + Offsets Workflow

#### 1. Base Schedule (from MC01)

Assume we have a base schedule from MC01 with one asset scheduled on YouTube Shorts (anchor channel):

```json
{
  "request_id": "req_shorts_2025",
  "tenant_id": "tenant_acme",
  "env": "prod",
  "slots": [
    {
      "slot_id": "base_shorts_001",
      "asset_id": "short_form_asset_001",
      "pool_id": "pool_short_form_001",
      "content_type": "short_form",
      "channel": "youtube_shorts",
      "scheduled_date": "2025-01-01"
    }
  ],
  "timeline_tasks": [...]
}
```

#### 2. Request Multi-Channel Schedule with Offsets

```json
POST /cadence/apply-offsets
{
  "request_id": "req_shorts_2025_mc02",
  "tenant_id": "tenant_acme",
  "env": "prod",
  "base_schedule_request_id": "req_shorts_2025",
  "anchor_channel": "youtube_shorts",
  "channel_offsets": {
    "instagram": 1,
    "tiktok": 3,
    "stories": 0
  }
}
```

#### 3. Response with Multi-Channel Schedule + Timeline

```json
{
  "request_id": "req_shorts_2025_mc02",
  "tenant_id": "tenant_acme",
  "env": "prod",
  "slots": [
    {
      "slot_id": "offset_shorts_day0_001",
      "asset_id": "short_form_asset_001",
      "pool_id": "pool_short_form_001",
      "content_type": "short_form",
      "channel": "youtube_shorts",
      "scheduled_date": "2025-01-01",
      "meta": {
        "anchor_channel": "youtube_shorts",
        "offset_days": 0
      }
    },
    {
      "slot_id": "offset_instagram_day1_001",
      "asset_id": "short_form_asset_001",
      "pool_id": "pool_short_form_001",
      "content_type": "short_form",
      "channel": "instagram",
      "scheduled_date": "2025-01-02",
      "meta": {
        "anchor_channel": "youtube_shorts",
        "offset_days": 1
      }
    },
    {
      "slot_id": "offset_tiktok_day3_001",
      "asset_id": "short_form_asset_001",
      "pool_id": "pool_short_form_001",
      "content_type": "short_form",
      "channel": "tiktok",
      "scheduled_date": "2025-01-04",
      "meta": {
        "anchor_channel": "youtube_shorts",
        "offset_days": 3
      }
    },
    {
      "slot_id": "offset_stories_day0_001",
      "asset_id": "short_form_asset_001",
      "pool_id": "pool_short_form_001",
      "content_type": "short_form",
      "channel": "stories",
      "scheduled_date": "2025-01-01",
      "meta": {
        "anchor_channel": "youtube_shorts",
        "offset_days": 0
      }
    }
  ],
  "conflicts": [],
  "timeline_tasks": [
    {
      "id": "task_offset_yt_001",
      "tenant_id": "tenant_acme",
      "env": "prod",
      "request_id": "req_shorts_2025_mc02",
      "title": "short_form on youtube_shorts (+0d)",
      "start_date": "2025-01-01",
      "lane": "youtube_shorts",
      "tags": ["short_form", "pool_short_form_001"],
      "source_id": "short_form_asset_001",
      "meta": {
        "anchor_channel": "youtube_shorts",
        "offset_days": 0,
        "base_slot_id": "base_shorts_001"
      }
    },
    {
      "id": "task_offset_ig_001",
      "tenant_id": "tenant_acme",
      "env": "prod",
      "request_id": "req_shorts_2025_mc02",
      "title": "short_form on instagram (+1d)",
      "start_date": "2025-01-02",
      "lane": "instagram",
      "tags": ["short_form", "pool_short_form_001"],
      "source_id": "short_form_asset_001",
      "meta": {
        "anchor_channel": "youtube_shorts",
        "offset_days": 1,
        "base_slot_id": "base_shorts_001"
      }
    },
    {
      "id": "task_offset_tiktok_001",
      "tenant_id": "tenant_acme",
      "env": "prod",
      "request_id": "req_shorts_2025_mc02",
      "title": "short_form on tiktok (+3d)",
      "start_date": "2025-01-04",
      "lane": "tiktok",
      "tags": ["short_form", "pool_short_form_001"],
      "source_id": "short_form_asset_001",
      "meta": {
        "anchor_channel": "youtube_shorts",
        "offset_days": 3,
        "base_slot_id": "base_shorts_001"
      }
    }
  ],
  "total_slots": 4,
  "date_range_start": "2025-01-01",
  "date_range_end": "2025-01-04",
  "meta": {
    "anchor_channel": "youtube_shorts",
    "channel_offsets": {
      "instagram": 1,
      "tiktok": 3,
      "stories": 0
    },
    "is_offset_applied": true
  }
}
```

Notes:
- **Determinism**: Offset slot IDs are stable hashes based on asset, channel, and offset-adjusted date.
- **Multi-Channel Expansion**: One base slot expands to 4 slots (one per configured channel) with deterministic timing.
- **Conflict Detection**: If offsets cause overlaps with existing cooldowns or per-channel caps, conflicts are surfaced (inherited from MC01 + checked for offset collisions).
- **Timeline Grouping**: Each task has `lane=channel` and inherits pool/content_type tags for timeline_core rendering.
- **Default Behavior**: If channel_offsets not provided, defaults apply (IG:+1, TikTok:+2, Stories:+0, etc.).



## 7. Guardrails  
- Do not touch auth/tenant/RequestContext code.  
- Do not touch /ui, /core, /tunes.  
- Do not modify connectors, orchestration flows, manifests, or Nexus/agent behaviour.  
- Do not add/change vector store / memory / logging pipelines.  
- Stay within allow-list; STOP on expansion.  

## 8. Execution note  
Workers must implement code+tests+docs strictly within the allow-list to meet DoD. If any work appears to require files outside the list, STOP and report. Once tests and checklist are complete, MC02 is DONE; subsequent phases can build on this mapping without breaking contracts.
