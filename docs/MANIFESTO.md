# Manifesto · NorthStar Engines

This is the human map for this repo.

If you only remember a few files, remember:

1. `README.md` – what this repo is.
2. `BOSSMAN.txt` – Jay’s ritual.
3. `docs/constitution/00_CONSTITUTION.md` – the laws.
4. `docs/constitution/01_FACTORY_RULES.md` – how work flows.
5. `docs/20_ENGINES_PLAN.md` – engines backlog and active tasks.
6. `docs/99_DEV_LOG.md` – what happened.
7. `docs/logs/ENGINES_LOG.md` – detailed engine task log.

## 1. Purpose of this repo

NorthStar Engines is where we build:

- Audio engines (ASR, TTS, music, mixing).
- Video engines (cutting, captioning, compositing).
- 3D engines (layout, scenes, render helpers).
- Analytics engines (metrics, scoring, reports).

These engines are meant to be:

- Agent-driven.
- UI-agnostic.
- Testable and composable.

UI / OS repos will call into these engines.

## 2. Laws and Rules

Read these first:

- `docs/constitution/00_CONSTITUTION.md`
- `docs/constitution/01_FACTORY_RULES.md`
- `docs/constitution/02_ROLES_AND_MODELS.md`

## 3. Role Playbooks

- Gem (Architect / Planner): `docs/GEMINI_PLANS.md`
- Max (Implementer): `docs/01_DEV_CONCRETE.md`
- Claude (Team Blue / QA): `docs/QA_TEAM_BLUE.md`
- Ossie (Styling / OSS): `docs/OSSIE_STYLE_GUIDE.md`

## 4. Engines Plan

- Global engines backlog and active task:
  - `docs/20_ENGINES_PLAN.md`

Gem owns the content and structure.  
Max updates status as phases complete.  
Claude stamps QA.

## 5. Logs

- Repo-wide dev log:
  - `docs/99_DEV_LOG.md`
- Engine task log:
  - `docs/logs/ENGINES_LOG.md`

No deleting old entries. New work gets new lines.

