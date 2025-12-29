# PHASE 06 — Minimal Audit Endpoints (Scaffolding)

Goal: Provide audit scaffolding so FE can wire “Run audit” flows. If real audits exist, standardize; otherwise create minimal placeholders that persist artifacts + Nexus metadata.

In-scope
- Audit endpoint(s) accepting render-ref/artifact-ref and routing keys; returns structured (possibly empty) report.
- Persist audit artifact (JSON) + DatasetEvent/Nexus document with lineage.
- Auth + tenant enforcement.

Out-of-scope
- Real audit logic (SEO/accessibility/perf) unless already implemented elsewhere.
- UI or orchestration prompts.

Allowed modules to change
- New audit router/module (e.g., `engines/canvas_audit/*`) or reuse existing logging/audit helper `engines/logging/audit.py`.
- media_v2/Nexus write paths as per PHASE 04.
- Tests under new audit module.

Steps
1) If existing audit engines are found (none today), surface them with auth/tenant + routing keys; otherwise create placeholder endpoint returning `{status:"ok", findings:[]}`.
2) Persist audit artifact (kind=audit) via media_v2 and Nexus metadata including routing keys, correlation_id, actor_id.
3) Emit DatasetEvent with audit context for legal/debug traceability.
4) Tests:
   - Tenant isolation on audit creation/read.
   - Audit artifacts stored and retrievable.
   - DatasetEvent emitted.
5) Stop conditions:
   - DO NOT continue if audit endpoints lack routing key or tenant validation.
   - DO NOT continue if artifacts are not persisted.

Do not touch
- No FE; no prompts/personas; no strategy/policy logic beyond auth/tenant enforcement.
