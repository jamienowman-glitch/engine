# Phase 2 — Event sink to BigQuery

Goal
- Make DatasetEvent/audit events persist to BigQuery as the primary ledger with clear dataset/table conventions and partitioning; keep Firestore for config/state.

Files to touch
- Nexus/logging backends: `engines/nexus/backends/*`, `engines/logging/events/*`
- Config wiring/env: `engines/config/runtime_config.py` (only if new vars are truly required)
- Docs for dataset/table conventions in this folder

Tests to run
- `python3 -m pytest engines/logging/events/tests`
- `python3 -m pytest engines/nexus/tests`
- Targeted BigQuery backend tests/mocks as added

Acceptance checklist
- BigQuery write path exists with partitioning strategy and table naming
- Firestore path remains intact for config/state
- DatasetEvent schema unchanged; adapter maps correctly
- Env vars documented; no silent fallbacks

Do not touch
- 3D/video/audio engines
- Frontend/UI
- Builder/media pipelines unrelated to event sink

Wrap-up
- Update `docs/workflows/88mph/00_MASTER_PLAN.md` to mark Phase 2 complete when done.
