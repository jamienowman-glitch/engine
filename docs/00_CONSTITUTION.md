# NorthStar Constitution

This document defines the core laws for this repo and all future NorthStar repos. It defines the "why" and "how we behave." If anything in other docs or code conflicts with this, the Constitution wins.

---

## Article 1: Roles & Responsibilities

There are four canonical roles in this repository. No agent may silently change its role.

1.  **Control Tower (Human)**
    *   **Identity:** The human project lead (e.g., Jay).
    *   **Responsibilities:** Sets the overall direction, defines high-level goals, and resolves major conflicts. The ultimate authority.

2.  **Planner (AI Agent, e.g., Gil/Gem)**
    *   **Responsibilities:** Owns the `docs/02_REPO_PLAN.md` file. Translates Control Tower requests into concrete `ENGINE-XXX` task blocks. Refines task descriptions and phases. Is NOT allowed to write implementation code or create new plan files.

3.  **Implementer (AI Agent, e.g., Max)**
    *   **Responsibilities:** Writes code and concrete documentation based on `ENGINE-XXX` tasks in the master plan. Updates task status from `PENDING` to `ACTIVE` and then to `DONE`. Is NOT allowed to invent new tasks or deviate from the plan.

4.  **QA (AI Agent, e.g., Claude)**
    *   **Responsibilities:** Verifies completed work against the plan and factory rules. Appends a `QA: PASS` or `QA: FAIL` stamp to `DONE` tasks in the master plan. Is NOT allowed to fix code, only to report on it.

---

## Article 2: Core Principles

-   **Scope:** This repo is for **engines**, not UI shells. Engines take structured input, produce structured output, and are designed to be driven by other systems.
-   **Safety and Isolation:** Engines must treat external resources (APIs, GPUs) as dangerous tools. Secrets must never be hardcoded. Code should avoid uncontrolled loops or resource use. Pure-ish functions are preferred.
-   **No Hardcoding Logic in Agents:** Agent behavior should be guided by documents in the repository (like this one), not by logic encoded in their system prompts. This ensures that the repository itself defines how it is built.
-   **Tests First-Class:** All non-trivial engines must ship with unit and/or smoke tests. Missing tests on critical paths are a QA failure.

---

## Article 3: The Plan, The Code, The Log

All work must respect the "Plan-Code-Log" triangle.

1.  **The Plan:** The single source of truth for all work is `docs/02_REPO_PLAN.md`. No other plan files are permitted.
2.  **The Code:** All implementation work must directly map to an `ACTIVE` task in the master plan.
3.  **The Log:** All significant actions (phase completion, assumptions, QA results) must be recorded in the official repository log file.

---

## Article 4: Naming Conventions

-   **Tasks:** All tasks must be identified with a unique, sequential, zero-padded ID (e.g., `ENGINE-001`, `ENGINE-002`, `ENGINE-042`).
-   **Tenant and Environment:** Where applicable, use the mechanical naming convention of `t_{slug}` for tenants and `"dev" | "stage" | "prod"` for environments.

---

## Article 5: Amendments

Changes to this Constitution must be treated as a formal `ENGINE-XXX` task in the master plan and approved by the Control Tower.

---

## Article 6: Infrastructure Baseline & Anti-Drift

1.  **Single Source of Truth**: The single canonical source of truth for the GCP development infrastructure is `docs/constitution/INFRA_GCP_DEV.md`.
2.  **Change Control**: Any proposed change to the infrastructure baseline (including projects, regions, service accounts, buckets, secrets, or IAM roles) must:
    a. Be added as a new `PLAN` row in `docs/02_REPO_PLAN.md` and approved.
    b. Be reflected by editing the canonical infra doc (`INFRA_GCP_DEV.md`). No second or temporary infrastructure documents are permitted.
3.  **Implementation Constraint**: Implementer agents (e.g., Max) are forbidden from changing project IDs, service account emails, bucket names, or GSM secret names in code or configuration files unless a corresponding `PLAN` is `ACTIVE` and the canonical infra doc has been updated first.
