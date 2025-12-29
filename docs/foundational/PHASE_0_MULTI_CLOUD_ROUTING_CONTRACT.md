# Phase 0 Multi-Cloud Routing Contract (GCS | S3 | Azure Blob) — Mode-only, No-InMemory

Scope: contract only; implementation deferred.

## Providers
- gcs (uri gs://bucket/path)
- s3 (uri s3://bucket/path)
- azure_blob (uri azure://account/container/path) — naming fixed; credentials/config TBD but shape must align with az storage account + container + sas/key.

## Selection policy (per tenant + mode + project)
- Inputs: tenant_id, mode (saas|enterprise|lab), project_id, surface/app (optional), resource_kind (raw/media_v2/replay/logs/etc.), policy overrides (cost/quality/outage/manual).
- Resolution: control-plane routing registry returns provider + target (bucket/container/account) per resource_kind scoped by tenant+mode+project. No env-based defaults.
- Overrides: manual override allowed by control-plane (e.g., force gcs or s3 or azure_blob) for outage/cost; t_system may override globally for lab/testing but still durable.

## Target representation
- GCS: gs://<bucket>/<key>
- S3: s3://<bucket>/<key>
- Azure: azure://<account>/<container>/<key>
Keys must include tenant/mode/project prefix (and surface/app when applicable); example: tenants/{tenant}/{mode}/raw/{asset_id}/{filename}.

## Required observability fields on every write
- Context: tenant_id, mode, project_id, surface_id/app_id (if applicable), request_id, trace_id, run_id, step_id, actor_id.
- Event envelope must carry provider + target URI + storage_class + result (ok/error) + timestamp.

## t_system override rules
- t_system can set global routing defaults for lab mode for bootstrap/testing, but must still be durable (no in-memory/noop).
- No other hardcoded tenants allowed.

## Minimal config keys (shape)
- gcs: GCS_PROJECT_ID, RAW_BUCKET (or per-kind bucket), credentials via ADC; registry entry records bucket.
- s3: AWS_REGION, RAW_BUCKET (or per-kind bucket), credentials via AWS_PROFILE/keys; registry entry records bucket.
- azure_blob: AZURE_STORAGE_ACCOUNT, AZURE_STORAGE_CONTAINER, AZURE_STORAGE_KEY or SAS token (exact names TBD but shape fixed to account/container/credential); registry entry records account+container.
