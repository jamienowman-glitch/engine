# Prod Launch Master Plan

Phases (execute in order; mark [ ] when done):
- [ ] PHASE 00 — Lane + Guardrails + Production Checklist (docs/workflows/prod_launch/PHASE_00_LANE_GUARDRAILS.md)
- [ ] PHASE 01 — Cognito Auth: Real JWT Verify + /auth/me (docs/workflows/prod_launch/PHASE_01_COGNITO_AUTH.md)
- [ ] PHASE 02 — Auto-Tenant Bootstrap + Membership Stub (docs/workflows/prod_launch/PHASE_02_TENANT_BOOTSTRAP.md)
- [ ] PHASE 03 — Projects + Threads Primitives (docs/workflows/prod_launch/PHASE_03_PROJECTS_THREADS.md)
- [ ] PHASE 04 — Session Memory + Message Bundle Forwarding (docs/workflows/prod_launch/PHASE_04_SESSION_MEMORY.md)
- [ ] PHASE 05 — Maybes Scratchpad + Forward-to-Maybe + Promote Hook (docs/workflows/prod_launch/PHASE_05_MAYBES.md)
- [ ] PHASE 06 — S3 Raw Storage + Signed URLs (docs/workflows/prod_launch/PHASE_06_S3_STORAGE.md)
- [ ] PHASE 07 — File Explorer Backend + Derived Views Registry (docs/workflows/prod_launch/PHASE_07_FILE_EXPLORER.md)
- [ ] PHASE 08 — Stripe Billing: Checkout + Webhook + Entitlements + Comps (docs/workflows/prod_launch/PHASE_08_BILLING.md)
- [ ] PHASE 09 — Safety/Audit/Prod Gate Sweep + Fail-Fast Config (docs/workflows/prod_launch/PHASE_09_SAFETY_AUDIT.md)
- [ ] PHASE 10 — Bossman Launch Dashboard v2 (docs/workflows/prod_launch/PHASE_10_BOSSMAN.md)

Open question for execution agents to resolve with owners:
- Domains/URLs for Cognito/Stripe callbacks/logout.
- Runtime secret injection path in deploy (placeholders documented per phase).

Non-negotiables (apply to all phases):
- No prompts/personas/orchestration logic in /engines; engines remain deterministic plumbing.
- Cards/manifests stay outside engines.
- Tenant/env required; user binding where applicable; missing config fails loud.
- Do not change KPI/Temperature semantics.
- Do not change Strategy Lock or Firearms semantics.
- Do not touch 3D/video/audio muscle engines unless explicitly named.
- No new env var names; reuse canonical ones only.
