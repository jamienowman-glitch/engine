# Prod Launch Workflow Lane
- This is the only authoritative lane for the production launch scope (auth, tenants, projects/threads, memory, Maybes, storage, explorer, billing, safety, Bossman v2). All other docs are reference-only unless explicitly cited by a phase.
- Execution agents must follow 00_MASTER_PLAN.md and the phase files in this folder; no improvisation or cross-scope edits.
- Engines remain deterministic plumbing: no prompts/personas/orchestration logic in /engines; cards/manifests stay outside engines.
- Tenant/env/user binding is mandatory for every route/service/store/log; missing config fails closed (no dev fallbacks).
