# Nexus Production Lane
- Scope: planning documents for Nexus production hardening. Engines remain deterministic plumbing only; no prompts, agent logic, or orchestration here.
- Active lanes: 00_MASTER_PLAN.md + phase files in this folder; referenced docs are read-only context only.
- Hard bans: no prompts in engines, no cards/manifests/orchestration logic, no behavior changes to KPI/Temperature semantics.
- Tenancy: every plan assumes tenant_id + env + user_id scoping from request boundaries through storage/indexing/logging; fail closed if missing.
- Media/3D/video/audio engines are off-limits unless explicitly targeted in a phase.
