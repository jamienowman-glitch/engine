# Phase 0.5 — Registry Single Source of Truth

- Source of truth = the registry schemas and enums living in `northstar-agents`.
- `northstar-engines` must consume those definitions (via direct import or a vendored snapshot) and must not redefine registry contracts in this repo.
- This applies to resource_kind names, tool IDs, connector scopes, and card schemas across engines subsystems.
- No drift: any update begins with a PR in `northstar-agents`, then engines delay-gate (bump dependency or refresh the snapshot) with an explicit reference to the agents change.
- Versioning workflow: describe the change in the agents repo, merge it, and then update engines by pulling the new schema/enum revision before the next deploy.
