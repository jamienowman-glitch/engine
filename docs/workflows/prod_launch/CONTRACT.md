# Prod Launch Contract (Guardrails for Execution Agents)

Non-negotiables (repeat in every phase):
- No prompts/personas/orchestration logic in /engines; engines stay deterministic plumbing.
- Cards/manifests live outside engines; do not introduce runtime card behavior in engines.
- Tenant/env binding always required; user binding where applicable; missing config fails loudly (no dev fallbacks).
- Do not change KPI or Temperature semantics.
- Do not change Strategy Lock or Firearms semantics; hook only where phases specify.
- Do not touch 3D/video/audio muscle engines (scene_engine, video_*, audio_*, animation_kernel, etc.) unless a phase explicitly names a small boundary module.
- No new env var names; reuse canonical ones already in repo.

Canonical context:
- RequestContext/AuthContext shapes in engines/identity/auth.py are authoritative; reuse them without modification.
- DatasetEvent, pii_flags, train_ok shapes are defined in engines/dataset/events/schemas.py; log via engines/logging/events.
- Storage/Nexus/S3 config names follow existing env vars documented under docs/infra/* and engines/config/runtime_config.py.

Enforcement rules for agents:
- Work only in files explicitly listed in the active phase’s “Affected modules”.
- If a needed file/path is not listed, stop and escalate; do not edit outside allowed paths.
- If tests in forbidden areas fail, document as known issue; do not “fix” by changing guarded semantics.
- Any missing config/secret must raise/400/500; never silently default.
