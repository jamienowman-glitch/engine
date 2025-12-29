# Phase 3 — Cost-of-goods-sold: AWS + GCP

Goal
- Extend current AWS identity/billing probe to cost priors/updates and surface Bossman credits/estimates/remaining across AWS+GCP.

Files to touch
- Budget: `engines/budget/*`
- AWS/GCP billing probes: `engines/common/aws_runtime.py`, analogous GCP helper if needed
- Bossman: `engines/bossman/routes.py` (extend response)
- Docs in this folder

Tests to run
- `python3 -m pytest engines/budget/tests`
- `python3 -m pytest tests/test_aws_runtime.py tests/test_aws_routes.py` (and GCP equivalents you add)
- Targeted Bossman endpoint tests

Acceptance checklist
- Priors/update mechanism for cost; ability to reconcile estimates when bills land
- Bossman exposes credits/est spend/remaining (best-effort) with clear freshness/source
- AWS probe retained; GCP probe added if needed
- No silent fallbacks; tenant/env scoped

Do not touch
- 3D/video/audio engines
- Frontend/UI
- Unrelated vector/media pipelines

Wrap-up
- Update `docs/workflows/88mph/00_MASTER_PLAN.md` to mark Phase 3 complete when done.
