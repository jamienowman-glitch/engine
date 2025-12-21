# Nexus Contract (Authoritative)

RequestContext required fields:
- tenant_id (required)
- env (required; normalized dev|staging|prod)
- user_id/auth_subject (required for user actions)
- membership_role (used for owner/admin gating)
- request_id/trace_id (required; synthesize if absent)

DatasetEvent canon:
- Fields: tenantId, env, surface, agentId, input, output, pii_flags, train_ok, metadata, trace_id/request_id, user_id/auth_subject.
- Requirements: tenant/env/user/trace required; PII redaction applied before persistence; audit events include action + subject + when.

Storage conventions (raw + atoms):
- Raw assets live in object storage (S3/GCS) at `tenants/<tenant_id>/<env>/raw/<asset_id>/<filename>`.
- Derived atoms live at `tenants/<tenant_id>/<env>/atoms/<artifact_id>/<filename>`; metadata stored with lineage refs.
- All records store tenant_id, env, asset/artifact ids, sha256, size_bytes, content_type, captured_at/imported_at, lineage refs.

Card format standard:
- Cards are “YAML header + NL body” separated by `---`.
- Minimal required header keys: card_id, card_type, version, tenant_id, env, created_at, created_by; allow unknown keys.
- Body is natural language; engines treat cards as opaque text, not interpreted prompts.
