# Nexus Production Master Plan

Boundaries:
- Engines are deterministic infrastructure only; no prompts, agent logic, or orchestration lives in /engines.
- Meaning/steering lives in cards/manifests in /core; engines only store/index/retrieve/log.
- Multi-tenant/user/env from day one; all routes/stores/logs require tenant_id + env (normalized) + auth context; fail closed if missing.
- KPI/Temperature semantics are locked; only hardening/validation/observability allowed where relevant.
- Nexus stance: raw → atoms → cards → retrieval → influence packs → logging; zero interpretation/ranking inside engines.
- PII pipeline enforced: pii_flags + train_ok + tenant/user opt-out on all persists/exports; redaction before logging.

Phases (execute in order; mark [ ] when done):
- [x] PHASE 0 — Repo lane + guardrails (docs/workflows/nexus/PHASE_00_LANE_GUARDRAILS.md)
- [x] PHASE 1 — Raw Storage (S3) + Tenancy + Lineage (docs/workflows/nexus/PHASE_01_RAW_STORAGE.md)
- [x] PHASE 2 — Atoms (Derived Artifacts) (docs/workflows/nexus/PHASE_02_ATOMS.md)
- [x] PHASE 3 — Cards (YAML + NL) (docs/workflows/nexus/PHASE_03_CARDS.md)
- [x] PHASE 4 — Indexing (Vector + Filters over Cards) (docs/workflows/nexus/PHASE_04_INDEXING.md)
- [x] PHASE 5 — Influence Packs (docs/workflows/nexus/PHASE_05_INFLUENCE_PACKS.md)
- [x] PHASE 6 — Settings & Control Screens APIs (docs/workflows/nexus/PHASE_06_SETTINGS.md)
- [x] PHASE 7 — Research Runs Log View (docs/workflows/nexus/PHASE_07_RESEARCH_RUNS.md)
- [x] PHASE 8 — Session Memory Placeholder (docs/workflows/nexus/PHASE_08_SESSION_MEMORY.md)
- [x] PHASE 9 — Production Hardening Checklist (docs/workflows/nexus/PHASE_09_PROD_GATES.md)
- [ ] Continuous — “No prompts in engines” sweep (docs/workflows/nexus/PHASE_CONT_NO_PROMPTS.md)

Final gate checklist (engines only):
- Tenant/env/user scoping enforced and tested across raw storage, atoms, cards, indexing, packs, settings, research runs, memory.
- Required config slots (auth, storage buckets, vector/index ids, backends) validated on startup; missing config fails closed.
- PII/redaction and audit logging applied on all writes/reads; DatasetEvents carry tenant/env/user/trace ids.
- Nexus limited to storage/index/logging and lineage; no semantic interpretation or orchestration; cards/manifests/orchestration live outside engines.
- Strategy Lock/role gating applied to definitions/index changes/settings edits where specified; KPI/Temperature meanings unchanged.
- Ready to run with 2+ tenants and 2+ users (owner/admin/member paths) without cross-tenant leakage.
