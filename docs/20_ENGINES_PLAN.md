# Engines Plan · NorthStar Engines

This is the central backlog and plan for engines work.

Plan ownership:
- Gem (Architect) owns structure and wording.
- Max (Implementer) updates status fields as phases complete.
- Claude (QA) stamps completed tasks with PASS/FAIL.

Pre-flight for anyone working on engines:
- Read:
  - `docs/constitution/00_CONSTITUTION.md`
  - `docs/constitution/01_FACTORY_RULES.md`
  - `docs/constitution/02_ROLES_AND_MODELS.md`
- Read:
  - `docs/engines.md`
  - This plan file.

---

## 1. Backlog / Future Tasks

These IDs are placeholders; Gem will flesh them out.

- `E-01` – Baseline project wiring
  - Goal: Set up minimal Python package structure and basic test harness.
- `E-02` – Audio Engine: simple ASR wrapper
  - Goal: Wrap a single ASR provider behind a clean interface.
- `E-03` – Video Engine: clip cutter
  - Goal: Implement a basic video cutter given start/end timestamps.
- `E-04` – 3D Engine: grid-to-world mapper
  - Goal: Map abstract 2D grid layouts into 3D scene coordinates.
- `E-05` – Analytics Engine: simple metrics aggregator
  - Goal: Aggregate basic metrics and output summaries.

Gem will:
- Turn each of these into a detailed task with phases.
- Add new tasks as the system evolves.

---

## 2. Active Task

At repo bootstrap there is no Active Task.

Gem’s first job in this repo is to:
- Choose which of E-01..E-05 to activate (or define a new E-XX).
- Promote it to Active Task by filling in the template below and moving the task out of Backlog.

### Active Task Template (to be filled by Gem)

Example structure Gem should use:

- Task ID: E-XX
- Goal: Short description.
- Files to touch:
  - src/...
  - tests/...
  - docs/...

#### Phase 1 – Name

- Goal:
- Files:
- Steps (Max / Implementer):
  1. ...
  2. ...
- Logging & Status (Max):
  - Append entry to `docs/logs/ENGINES_LOG.md` with:
    - `YYYY-MM-DD · E-XX · P1 · Done · Short note · Commit/hash`
  - Mark this Phase as Done in this plan.

#### Phase 2 – Name

- Goal:
- Files:
- Steps (Max / Implementer):
  1. ...
  2. ...
- Logging & Status (Max):
  - Same pattern as Phase 1.

(Additional phases as needed.)

### Task Completion Ritual (Max)

When all phases of the Active Task are Done:

- Move the whole task block from **Active Task** → **Completed Tasks** in this file.
- Confirm that:
  - Each phase has an entry in `docs/logs/ENGINES_LOG.md`.
- Leave any QA work for Claude.

---

## 3. Completed Tasks

None yet.

Claude will:
- Add QA stamps under tasks in this section after reviewing them.

