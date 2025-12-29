# Phase S3 Smoke Test Report (read/verify only, no code changes)

## Target bucket discovery
- RAW_BUCKET env value: None (python3 -c "from engines.config import runtime_config; print(runtime_config.get_raw_bucket())" → None).
- Repo references: engines/nexus/raw_storage/repository.py:35-123; engines/config/runtime_config.py:82-83 uses env RAW_BUCKET; media_v2 also requires RAW_BUCKET (engines/muscle/media_v2/service.py:59-69).
- Decision: S3 expected (S3RawStorageRepository uses boto3); bucket not set in current environment, so smoke write skipped.

## Credential resolution (aws cli)
- env | egrep 'AWS_|RAW_BUCKET|S3_': AWS_DEFAULT_REGION=us-east-1; AWS_PROFILE=northstar-dev.
- aws --version: aws-cli/2.32.14 Python/3.13.11 Darwin/24.2.0 source/arm64.
- aws configure list:
  - profile: northstar-dev (env: AWS_PROFILE)
  - access_key/secret_key from shared-credentials-file (~/.aws/credentials)
  - region: us-east-1 from env.
- aws sts get-caller-identity:
  - Account: 521176575081
  - Arn: arn:aws:iam::521176575081:user/northstar-dev
- Source of truth: ~/.aws/credentials `[northstar-dev]` (key/secret); ~/.aws/config `[profile northstar-dev]` region us-east-1. Active via AWS_PROFILE env.

## Smoke test
- Not executed: RAW_BUCKET is unset → no target key to write. No presign or s3 cp attempted.

## Remediation (no key re-entry)
- Set RAW_BUCKET in the environment (e.g., export RAW_BUCKET=<bucket>) or in a runtime config file loaded before engines start. Ensure workers inherit AWS_PROFILE=northstar-dev and HOME pointing to ~/.aws/credentials. If workers run in non-interactive shells, confirm they still see AWS_PROFILE and the credential files (e.g., set in process env or launchctl).

## Commands run (outputs above)
- env | egrep 'AWS_|RAW_BUCKET|S3_' || true
- aws --version
- aws configure list
- aws sts get-caller-identity
- python3 - <<'PY' from engines.config import runtime_config; print(runtime_config.get_raw_bucket()) PY
