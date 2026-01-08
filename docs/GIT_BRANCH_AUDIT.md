# Git Branch Audit

**Date:** 2026-01-07
**Remote:** origin (https://github.com/jamienowman-glitch/engine.git)

## Branch Analysis

| Branch Name | Status | Last Commit | Notes |
| :--- | :--- | :--- | :--- |
| `origin/backup/engines-smoke-20251230-2155` | **NOT MERGED** | 2025-12-30 | Keep. |
| `origin/gate2/audit-hash-chain` | **NOT MERGED** | 2025-12-30 | Keep. |
| `origin/gate3/ws-hello-ticket` | **NOT MERGED** | 2025-12-30 | Keep. |

## Main Branch Integrity

**Status:** 🔴 FAILED
**Validation:** `pytest` failed during collection.
**Reason:** `ImportError: cannot import name 'LicenceStatus' from 'engines.firearms.models'`.
**Root Cause:** 
- `origin/main` was successfully merged (bringing in `MaybeSourceType` fix).
- However, local unpushed commits (or staged changes) have refactored `engines/firearms/models.py`, removing `LicenceStatus`.
- `engines/bossman/routes.py` (existing file) still imports `LicenceStatus`.
- This indicates the local work-in-progress refactor of `firearms` is incomplete or incompatible with existing consumers (`bossman`).

**Action Taken:** 
- Synced `main` (pulled `origin/main`).
- Ran tests: Failed.
- **DID NOT PUSH** to avoid breaking the remote build.
- Recommended fixing `engines/bossman` to align with new `firearms` models before pushing.
