# LANE B – Codex Mini Execution Prompt

## Scope lock
Allowed files/modules only:
- `engines/nexus/raw_storage/routes.py`
- `engines/nexus/atoms/routes.py`
- `engines/nexus/packs/routes.py`
- `engines/nexus/cards/routes.py`
- `engines/nexus/index/routes.py`
- `engines/nexus/settings/routes.py`
- `engines/nexus/runs/routes.py`
- `engines/nexus/memory/routes.py`
- `engines/nexus/*/tests/*`
- `engines/logging/audit.py`
- `engines/logging/events/engine.py`
- `engines/dataset/events/schemas.py`
- `engines/logging/events/tests/*`
- `engines/maybes/service.py`
- `engines/feature_flags/models.py`
- `engines/feature_flags/repository.py`
- `engines/feature_flags/service.py`
- `engines/feature_flags/routes.py`
- `engines/feature_flags/tests/*`
- `engines/privacy/train_prefs.py`
- `engines/privacy/routes.py`
- `engines/privacy/tests/*`
- `engines/common/identity.py` (only if user_id validation needed)

If a change would touch any other file, STOP.

## Phases to execute (in order)
1) PHASE_02_NEXUS_AUTH_CONTEXT_ENFORCEMENT
2) PHASE_04_AUDIT_LOGGING_TRACE_IDS_IMMUTABILITY
3) PHASE_05_GLOBAL_FEATURE_FLAGS_TENANT0_LAYER
4) PHASE_07_PRIVACY_TRAIN_PREFS_API_PERSISTENCE

## STOP IF rules
- STOP if out-of-scope file needs modification.
- STOP if a change would weaken auth/tenant enforcement or bypass RequestContext.
- STOP if schema/endpoint changes are inferred rather than discovered in code.
- STOP if tests fail and require touching shared modules not listed.

## PR breakdown
- 1 PR per phase above (4 PRs). Keep PRs phase-scoped and small.

## Required tests per PR
- Phase 2: `pytest engines/nexus/*/tests`
- Phase 4: `pytest engines/logging/events/tests`
- Phase 5: `pytest engines/feature_flags/tests`
- Phase 7: `pytest engines/privacy/tests`
- Before merging the last Lane B PR: run combined `pytest engines/nexus/*/tests engines/logging/events/tests engines/feature_flags/tests engines/privacy/tests`

## Acceptance / handoff checklist per PR
- Changes confined to allowed files.
- RequestContext + get_auth_context enforced on Nexus routes; `assert_context_matches` applied to payloads.
- Audit logger now non-noop with trace_id/request_id/actor metadata; no silent failures.
- Feature flags support tenant-0 fallback; owner/admin-only writes enforced.
- Privacy training prefs APIs authenticated and persisted; logging engine respects stored prefs.
- Tests listed above passed locally with command output summary.
- Call out any shared-module edits (identity/auth/logging contracts) for integration coordination.
