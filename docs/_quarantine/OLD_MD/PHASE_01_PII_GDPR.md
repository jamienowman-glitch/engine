# Phase 1 — PII & GDPR primitive (must-have)

Goal
- Production-ready PII/GDPR posture for training/tuning exports: strip/redact PII for export paths, enforce tenant/user opt-out (`train_ok`), and propagate `pii_flags` on DatasetEvents without breaking tenant runtime content.

Files to touch
- PII guardrail: `engines/guardrails/pii_text/*` (detection/masking and schemas)
- Logging pipeline: `engines/logging/events/engine.py`
- DatasetEvent schema/tests if needed: `engines/dataset/events/schemas.py`, `engines/dataset/events/tests/*`
- Any new export-specific helpers (if needed) under `engines/` (avoid 3D/video/audio)

Tests to run
- `python3 -m pytest engines/guardrails/pii_text/tests`
- `python3 -m pytest engines/logging/events/tests`
- Add/adjust targeted tests if new helpers added

Acceptance checklist
- PII detection/masking covers emails, phones, cards, postal; outputs `pii_flags`
- `train_ok`/opt-out enforced per tenant/user for export-only flows (no impact on runtime responses)
- DatasetEvents carry `pii_flags` and train eligibility; redaction strategy keeps runtime usefulness (no over-redaction)
- Audit/logging emits PII metadata; docs updated in this folder if behavior changes

Do not touch
- 3D/video/audio engines
- UI/frontend assets
- Any unrelated builder/scene/video code

Wrap-up
- Update `docs/workflows/88mph/00_MASTER_PLAN.md` to mark Phase 1 complete when done.
