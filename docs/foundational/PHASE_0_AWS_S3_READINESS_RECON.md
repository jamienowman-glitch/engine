# Phase 0 AWS/S3 Readiness Recon (verification-only, no code changes)

Scope: northstar-engines raw storage paths.

1) Modules handling raw storage / presign / buckets
- Raw storage repository (S3) at engines/nexus/raw_storage/repository.py:35-123 — generates presigned POST, enforces bucket/key format, uses boto3.
- GCS client (for other media) at engines/storage/gcs_client.py:17-75 — not S3; included for awareness.

2) Env vars required (from engines/nexus/raw_storage/repository.py)
- RAW_BUCKET (bucket name) — required; ValueError if missing (lines 43-49).
- Env values validated: tenant_id regex ^t_[a-z0-9_-]+$ and env in {dev, staging, prod, stage} (lines 14-72) — to be replaced by mode later.
- AWS credentials/region: not explicitly read in code; boto3 uses standard AWS_* env/credentials chain.

3) Checks to run (non-destructive + optional smoke)
- Non-destructive identity + bucket check:
  - `aws sts get-caller-identity`
  - `aws s3api head-bucket --bucket "$RAW_BUCKET"`
- Optional minimal presign/upload/delete (only if creds available):
  - Use repo presign flow: `python - <<'PY'\nfrom engines.nexus.raw_storage.repository import S3RawStorageRepository\nrepo = S3RawStorageRepository()\nurl, fields = repo.generate_presigned_post(tenant_id=\"t_system\", env=\"lab\", asset_id=\"asset_smoke\", filename=\"ping.txt\", content_type=\"text/plain\")\nprint(url, fields)\nPY`
  - Then curl upload: `curl -X POST -F "key=${fields[key]}" -F "Content-Type=text/plain" -F "file=@/etc/hosts" $(for k in "${!fields[@]}"; do echo -n "-F ${k}=${fields[$k]} "; done) "$url"`
  - Verify: `aws s3api head-object --bucket "$RAW_BUCKET" --key "tenants/t_system/lab/raw/asset_smoke/ping.txt"`
  - Cleanup: `aws s3api delete-object --bucket "$RAW_BUCKET" --key "tenants/t_system/lab/raw/asset_smoke/ping.txt"`

4) Notes/gaps
- Validation still uses legacy env set; must switch to mode (saas|enterprise|lab).
- Metadata persistence is a noop for S3 (repository.py:104-107); durability of metadata must be added later.
