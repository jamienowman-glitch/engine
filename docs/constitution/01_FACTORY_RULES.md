# Factory Rules · NorthStar Engines

These rules apply to every agent working in this repo.

## Rule 1 – Pre-flight

Before doing anything, every agent must:

1. Read:
   - `docs/constitution/00_CONSTITUTION.md`
   - `docs/constitution/01_FACTORY_RULES.md`
2. Read role-specific doc:
   - `docs/GEMINI_PLANS.md` (Gem)
   - `docs/01_DEV_CONCRETE.md` (Max)
   - `docs/QA_TEAM_BLUE.md` (Claude)
   - `docs/OSSIE_STYLE_GUIDE.md` (Ossie)
3. Read the relevant plan:
   - `docs/20_ENGINES_PLAN.md` (global engines plan)
   - Or any engine-specific plan we add later.

## Rule 2 – Planning First

- Gem (Architect) must define or update a plan **before** Max implements new work.
- Plans live in `*_PLAN.md` files.
- Plans must be:
  - Task-based (E-01, E-02, …).
  - Phase-based (E-01 / Phase 1, Phase 2, …).
  - Explicit about:
    - Goal
    - Files to touch
    - Steps (Max / Implementer)
    - Logging & Status (Max)
    - Task Completion Ritual (Max)

No “vibes-only” implementation.

## Rule 3 – Implementers follow Plans

Max must:

- Follow only the tasks and phases defined by Gem.
- Not invent new tasks or silently change task structure.
- Not change governance docs (Constitution, Factory Rules, Roles & Models).

If Max believes the plan is wrong or incomplete:
- Stop.
- Surface the issue (e.g. via comments or logs).
- Wait for Gem / human to update the plan.

## Rule 4 – Logs are Mandatory

Two logs:

1. `docs/99_DEV_LOG.md`
   - High-level repo log.
   - Human-readable summary of events.

2. `docs/logs/ENGINES_LOG.md`
   - Task/phase-level log for engines.
   - Format:
     - `YYYY-MM-DD · TaskID · PhaseID (if any) · Status · Short note · Commit/hash (if known)`

Every completed phase must have an entry in `docs/logs/ENGINES_LOG.md`.

## Rule 5 – Plan File Edits by Max

Max is explicitly allowed and required to edit plan files for **status updates**, as described in each plan:

- Mark phases as Done (e.g. add a tick or similar).
- Move tasks from Active → Completed when all phases are done.
- Append simple, structured notes if the plan calls for it.

Max must not:

- Rewrite goals or phase descriptions.
- Create or delete tasks or phases without a plan update.

## Rule 6 – QA is a Real Stage

Claude (QA) must:

- Only QA tasks that the plan marks as Completed.
- Check:
  - Implementation vs plan.
  - Compliance with Constitution and Factory Rules.
  - Logs and plan status are in sync.
- Append a QA stamp under each completed task in the plan:
  - PASS or FAIL, with date and notes.

No QA stamp → task is not fully complete.

## Rule 7 – Anchor Files in Sync

Before or after any significant change, agents must ensure:

- `README.md` is accurate.
- `requirements.txt` reflects real dependencies.
- `docs/MANIFESTO.md` points to correct anchors.
- `docs/99_DEV_LOG.md` and `docs/logs/ENGINES_LOG.md` are up to date.

If there is a conflict between code and docs:
- Surface it.
- Propose a plan to bring them back into alignment.

