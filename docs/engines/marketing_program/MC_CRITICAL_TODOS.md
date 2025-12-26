# MC_CRITICAL_TODOS

For feral worker agents. Obey STOP RULEs in PHASE_MC01 and PHASE_MC02. Engines-only; no auth/UI/core/connector/orchestration changes.

## MC01 Cadence Core
- [x] **MC01.1 [BLOCKER] Models & validation** — engines/marketing_cadence/models.py; tests/test_models.py. Define ContentPool, CadenceAsset, CooldownRule, enums; validate tenant/env/request_id, min_days_between_repeats, asset cooldown; deterministic hash/id helpers. ✅ COMPLETE
- [x] **MC01.2 [BLOCKER] Pool/asset CRUD routes** — engines/marketing_cadence/routes.py, service.py; tests/test_routes.py. CRUD/list pools/assets; 4xx on invalid payloads; tenant/env required in requests. ✅ COMPLETE
- [x] **MC01.3 [BLOCKER] Scheduler with cooldowns** — engines/marketing_cadence/service.py; tests/test_service.py. Given date range + pools/assets, propose slots per channel/type respecting pool and asset cooldowns; deterministic ordering; conflicts surfaced. ✅ COMPLETE
- [x] **MC01.3a [BLOCKER] Defaults and caps** — engines/marketing_cadence/service.py; tests/test_service.py. Apply default caps/cooldowns per content_type (stories, short_form incl. trial, long_form, email/dm flows/broadcasts, feed/carousels/community, blog/homepage) and global caps (target 5–7/day, hard cap 10/day; per-channel caps first). Tests assert defaults applied when not overridden. ✅ COMPLETE
- [x] **MC01.4 [BLOCKER] Conflict reporting** — engines/marketing_cadence/service.py; tests/test_service.py. Include conflicts for cooldown violations or insufficient assets; tests assert conflict meta. ✅ COMPLETE
- [x] **MC01.5 [QUALITY] Timeline adapter stub** — engines/marketing_cadence/service.py; tests/test_service.py. Emit timeline_core-shaped payload (lanes=channels, tags=content_type/pool) with stable ids/hashes; deterministic across runs. ✅ COMPLETE
- [ ] **MC01.6 [DOCS] Examples** — docs/engines/marketing_program/PHASE_MC01_cadence_core.md. Add JSON examples: pools/assets, schedule request (14-day), response with slots/conflicts + timeline stub.

## MC02 Anchor Offsets to Timeline
- [x] **MC02.1 [BLOCKER] Anchor/offset models** — engines/marketing_cadence/models.py; tests/test_offsets.py. Add anchor_channel + offsets per content_type; validate integers. ✅ COMPLETE
- [x] **MC02.2 [BLOCKER] Offset application service** — engines/marketing_cadence/service.py; tests/test_offsets.py. Apply offsets to base schedule, enforce determinism, surface conflicts on collisions/cooldowns. ✅ COMPLETE
- [x] **MC02.3 [BLOCKER] Timeline mapping with offsets** — engines/marketing_cadence/service.py; tests/test_timeline_mapping.py. Map offset schedule to timeline_core shape; stable ids/hashes; grouped by channel/content_type. ✅ COMPLETE
- [x] **MC02.4 [BLOCKER] Offset route** — engines/marketing_cadence/routes.py; tests/test_offsets.py. Endpoint to request offset-applied schedule + timeline payload; 4xx on invalid anchor/offsets. ✅ COMPLETE
- [ ] **MC02.5 [DOCS] Examples** — docs/engines/marketing_program/PHASE_MC02_anchor_offsets_to_timeline.md. Add example: anchor=YouTube Shorts, offsets IG:+1/TikTok:+3 → schedule + timeline JSON.
