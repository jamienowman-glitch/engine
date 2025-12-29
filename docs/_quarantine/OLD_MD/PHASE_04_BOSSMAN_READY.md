# Phase 4 — Bossman UI backend readiness

Goal
- Harden Bossman dashboard/backend schema for production: stable response shape, pagination/windows, explicit freshness, no hidden fallbacks.

Files to touch
- Bossman routes/services: `engines/bossman/routes.py`
- Any shared DTOs/schemas in engines used by Bossman sections
- Tests under `tests/` for Bossman endpoint coverage
- Docs in this folder

Tests to run
- `python3 -m pytest tests/test_bossman_dashboard.py` (extend as needed)
- Targeted schema/contract tests you add

Acceptance checklist
- Response schema stable and documented
- Pagination/windowing implemented where applicable (snapshots, locks, etc.)
- Freshness/source fields explicit
- No hidden or dev fallbacks in responses

Do not touch
- 3D/video/audio engines
- Frontend/UI assets

Wrap-up
- Update `docs/workflows/88mph/00_MASTER_PLAN.md` to mark Phase 4 complete when done.
