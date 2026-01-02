# Phase 0.5 — Infra Cloud Access Checklist (Diagnostic)

## Minimal roles (no org-admin assumed)
- GCP: project-level roles/storage.objectAdmin (or writer) for GCS; datastore.user for Firestore; bigquery.dataEditor if BigQuery used; serviceusage.serviceUsageConsumer to enable APIs. Prefer Workload Identity/OIDC; avoid user keys.
- AWS: IAM permissions for S3 (s3:PutObject/GetObject/ListBucket); DynamoDB/Athena if used later. Prefer OIDC/IAM roles; avoid long-lived access keys.
- Azure: Storage Blob Data Contributor for Blob; Cosmos DB Data Contributor if used; Service Principal via federated credentials recommended.

## CI auth recommendation
- Use OIDC (GitHub Actions/GitLab/Jenkins) or GCP Workload Identity Federation to assume roles / impersonate service accounts. No static keys in repo.

## CLI sanity checks (non-Org)
- GCP: `gcloud auth list`; `gsutil ls gs://<bucket>`; `gcloud firestore databases list`; `bq ls`; expect permission errors only if scoped resource denied.
- AWS: `aws sts get-caller-identity`; `aws s3 ls s3://<bucket>`; expect AccessDenied if bucket perms missing (not Organizations).
- Azure: `az account show`; `az storage container list --account-name <acct>` with login; expect permission errors if role missing.

## AccessDenied meaning (quick map)
- GCP PermissionDenied on org/billing APIs ≠ org-admin; verify project-level roles. Firestore/BigQuery AccessDenied usually project IAM scope.
- AWS AccessDenied on s3:ListBucket ≠ org/billing; means bucket policy/IAM role lacks permission.
- Azure AuthorizationFailed on storage/Cosmos usually role assignment missing; not tenant admin requirement.
