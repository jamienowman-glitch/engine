# Phase 6 — “What’s running” / “kill switches”

Goal
- Expose endpoints to list active workers/jobs/background spenders and provide global “turn off automation/autonomous mode” switches per tenant.

Files to touch
- New endpoints/services for status/switches under appropriate engines (exclude 3D/video/audio)
- Bossman or debug routes if used for visibility
- Docs in this folder

Tests to run
- Targeted endpoint/service tests verifying listing + kill switch behavior
- Any existing worker/job tests impacted

Acceptance checklist
- Endpoint(s) list active workers/jobs/background spenders (tenant/env scoped)
- Tenant-level switches to disable automation/autonomous mode
- Tests validate toggles and visibility

Do not touch
- 3D/video/audio engines
- Frontend/UI

Wrap-up
- Update `docs/workflows/88mph/00_MASTER_PLAN.md` to mark Phase 6 complete when done.
