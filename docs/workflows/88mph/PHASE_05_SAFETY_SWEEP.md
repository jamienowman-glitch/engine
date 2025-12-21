# Phase 5 — Safety sweep completion

Goal
- Ensure all state-changing routes are gated appropriately (Strategy Lock and/or Firearms) and document the gate matrix.

Files to touch
- Route gating checks across engines (exclude 3D/video/audio unless explicitly targeted)
- Strategy Lock/Firearms docs: `docs/infra/AUTH_TENANT_SPINE_DEV_RUN.md` (gate matrix)
- Tests for gated routes

Tests to run
- Targeted route tests per engine touched
- Existing gating tests (Strategy Lock, Firearms)

Acceptance checklist
- Every state-changing route is gated (Strategy Lock and/or Firearms) or explicitly documented why not
- Gate matrix documented
- Tests cover gated/blocked paths

Do not touch
- 3D/video/audio engines
- Frontend/UI

Wrap-up
- Update `docs/workflows/88mph/00_MASTER_PLAN.md` to mark Phase 5 complete when done.
