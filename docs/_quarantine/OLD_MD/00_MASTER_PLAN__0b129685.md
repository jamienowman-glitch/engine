# 88mph Maybes + Production Hardening Master Plan

Non-negotiables (do not touch):
- Strategy Lock behavior/semantics/enforcement.
- Firearms behavior.
- Tenant/Auth canonical shapes (RequestContext/AuthContext/JWT flow).
- Temperature/KPI semantics.
- 3D/video/audio engines (scene_engine, video_*, audio_*, animation_kernel, etc.).
- No hardcoded prompts or agent behavior in engines.
- No new env var names; reuse canonical ones only.

Phases (execute in order; mark [ ] when done):
- [ ] PHASE 1 — Maybes audit + contract lock (docs/workflows/88mph/PHASE_01_MAYBES_CONTRACT.md)
- [ ] PHASE 2 — Maybes persistence + safety metadata (docs/workflows/88mph/PHASE_02_MAYBES_PERSISTENCE.md)
- [ ] PHASE 3 — “Save to Maybe” + “Forward” primitives (docs/workflows/88mph/PHASE_03_MAYBES_PRIMITIVES.md)
- [ ] PHASE 4 — Production readiness pass (docs/workflows/88mph/PHASE_04_PROD_READINESS.md)
- [ ] PHASE 5 — Guardrail sweep (docs/workflows/88mph/PHASE_05_GUARDRAILS.md)

For each phase:
- Goal: what “done” means.
- Success criteria: measurable checks.
- Touched paths: exact files/modules.
- DO NOT TOUCH reminder: restate fences above.

Open Questions:
- Should Maybes be scoped tenant-only or tenant+user by default?
- Retention/TTL default (off unless explicitly required?).
- Is Maybes included in tuning export (default no unless train_ok and operator-enabled)?
