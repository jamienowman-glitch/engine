# NorthStar Factory Rules

These rules define the process of building in this repository: the "how we build." They apply to every agent and human working here.

---

## Rule 1: Pre-flight Checklist

Before starting any work, every agent must read and understand:
1.  `docs/00_CONSTITUTION.md`
2.  `docs/01_FACTORY_RULES.md`
3.  `docs/02_REPO_PLAN.md` (to find the active task)

---

## Rule 2: The Master Plan Lifecycle

All work is driven by `ENGINE-XXX` tasks in `docs/02_REPO_PLAN.md`.

-   **Planner (Gil/Gem):**
    1.  Adds new tasks to the "Parking Lot" or promotes them to "B. Engine Tasks" with `Status: PENDING`.
    2.  Fills out the task template completely, including the `Ritual` section.
    3.  To kick off work, a Planner may change a task's status from `PENDING` to `ACTIVE`.

-   **Implementer (Max):**
    1.  Selects an `ACTIVE` task. If the status is `PENDING`, changes it to `ACTIVE`.
    2.  Follows the `Phases` in order.
    3.  Upon completing all phases, changes the task `Status: ACTIVE` to `Status: DONE`.
    4.  Appends a completion note under the task block: `Completed: <YYYY-MM-DD> – <short note>`.

-   **QA (Claude):**
    1.  Only reviews tasks with `Status: DONE`.
    2.  Appends a QA note under the task block: `QA: PASS (<YYYY-MM-DD>) – <notes>` or `QA: FAIL (<YYYY-MM-DD>) – <reason>`.

---

## Rule 3: Logging Ritual

A central log is kept at `docs/logs/ENGINES_LOG.md`.
-   The Implementer MUST log the completion of every phase of a task.
-   **Log Format:** `YYYY-MM-DD · <ENGINE_ID.Phase> · <Status> · <Short description of work>`
-   **Example:** `2025-12-01 · ENGINE-001.A · DONE · Defined Scene Engine contracts + types.`
-   Assumptions made during implementation must also be logged.

---

## Rule 4: Atomic File Structure

All new engines must follow a strict, separated file structure. This is non-negotiable.

-   `engine.py`: Contains the core `run()` function and minimal, pure helper logic.
-   `schemas.py`: Contains only Pydantic type definitions for inputs and outputs.
-   `tests/`: Contains `pytest` tests for the engine's functionality and schemas.
-   `service/` (if applicable): Contains FastAPI routers and HTTP-specific logic.

**CRITICAL:** Do not mix HTTP service logic, core business logic (`run`), and Pydantic schemas in the same file.

---

## Rule 5: Anchor Files

The following files are "anchor files" and must always be kept in sync with reality:
-   `README.md`
-   `requirements.txt`
-   `docs/00_CONSTITUTION.md`
-   `docs/01_FACTORY_RULES.md`
-   `docs/02_REPO_PLAN.md`
-   `docs/logs/ENGINES_LOG.md`

If any agent discovers a conflict between these files and the state of the codebase, their first duty is to report it or create a task to fix it.
