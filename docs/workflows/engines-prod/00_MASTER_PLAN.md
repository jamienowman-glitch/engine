# Engines Production Readiness Master Plan

Boundaries:
- Deterministic engines only; no prompts/cards/manifests/orchestration in engines; KPI/Temperature semantics locked (hardening only via validation/observability/config tests).
- Multi-tenant/user/env from day one; fail loud on missing tenant/env/auth; no cross-tenant caches.
- Nexus stance: raw → atoms → storage → retrieval only; no meaning/ranking/interpretation or card logic inside engines.

Phases (execute in order; mark [ ] when done):
- [ ] PHASE 01 — Tenant/User Runtime (docs/workflows/engines-prod/PHASE_01_TENANT_USER_RUNTIME.md)
- [ ] PHASE 02 — PII + GDPR + Audit (docs/workflows/engines-prod/PHASE_02_PII_GDPR_AUDIT.md)
- [ ] PHASE 03 — Logging + Traceability (docs/workflows/engines-prod/PHASE_03_LOGGING_TRACEABILITY.md)
- [ ] PHASE 04 — Nexus Primitives (docs/workflows/engines-prod/PHASE_04_NEXUS_PRIMITIVES.md)
- [ ] PHASE 05 — Raw Storage (S3/GCS) (docs/workflows/engines-prod/PHASE_05_RAW_STORAGE_S3.md)
- [ ] PHASE 06 — Vector Access (docs/workflows/engines-prod/PHASE_06_VECTOR_ACCESS.md)
- [ ] PHASE 07 — Session + Memory Pointers (docs/workflows/engines-prod/PHASE_07_SESSION_MEMORY.md)
- [ ] PHASE 08 — Safety Final Sweep (docs/workflows/engines-prod/PHASE_08_SAFETY_FINAL_SWEEP.md)
- [ ] PHASE 09 — Prod Gates (docs/workflows/engines-prod/PHASE_09_PROD_GATES.md)

Final gate checklist (engines only):
- Tenant/user/env scoping enforced on every route/service/store; isolation tests cover 2+ tenants and 2+ users (owner/admin/member paths).
- Required config slots (tenant/env/auth/storage/nexus/vector) validated; missing config fails closed.
- PII/Redaction pipelines applied before persistence/logging; audit trails carry tenant/env/user/trace ids.
- Nexus limited to raw artifacts, atoms, lineage, vector primitives, and access logging; zero semantic interpretation.
- KPI/Temperature: schemas/validation/observability hardened without changing meanings; Strategy Lock gating in place for definition/threshold edits.
- Storage/vector paths tenant/env scoped with retention/indexing; DatasetEvents emitted for write/read paths.
- Cards/manifests/orchestration live outside engines; engines only load pointers and log accesses.
