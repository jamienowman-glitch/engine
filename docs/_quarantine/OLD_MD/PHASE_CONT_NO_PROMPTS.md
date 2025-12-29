# Continuous — “No Prompts in Engines” Enforcement Sweep

Goal:
- Continuously ensure engines stay free of prompts/agent/orchestration logic; engines remain deterministic plumbing.

In-scope (engines only):
- Automated/manual sweeps of /engines for hardcoded prompts, agent role text, orchestration logic.
- Allow list: tool wrappers, deterministic transforms, routing to configured slots (SELECTA), storage/index/log plumbing.
- Violations are relocated to /core cards/manifests (outside engines) by future agents; engines keep only pointers/logging.
- DatasetEvents for enforcement actions optional; doc updates in lane when violations found.

Out-of-scope:
- Adding new behavior layers inside engines; changing KPI/Temperature semantics.

Affected engine modules:
- All `/engines/*` code; emphasis on chat/orchestration/logging/scene engines to catch drift.

Runtime guarantees added:
- None new; guardrail to maintain deterministic scope and multi-tenant posture.

What coding agents will implement later:
- Add search scripts/checks; fail CI/PRs on prompt/orchestration strings; document relocation steps.

How we know it’s production-ready:
- Sweeps scripted and documented; recent run shows no prompt/agent/orchestration strings in engines; exceptions recorded in allow list.
