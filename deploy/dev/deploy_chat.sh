#!/usr/bin/env bash
set -euo pipefail

SERVICE=northstar-engines-chat
IMAGE=gcr.io/northstar-os-dev/northstar-engines:latest
REGION=us-central1

gcloud run deploy "$SERVICE" \
  --image "$IMAGE" \
  --region "$REGION" \
  --platform managed \
  --service-account northstar-dev-engines@northstar-os-dev.iam.gserviceaccount.com \
  --allow-unauthenticated \
  --port 8000 \
  --set-env-vars GCP_PROJECT_ID=northstar-os-dev,GCP_REGION=us-central1 \
  --update-secrets TENANT_ID=northstar-dev-tenant-0-id:latest,RAW_BUCKET=northstar-dev-raw-bucket:latest,DATASETS_BUCKET=northstar-dev-datasets-bucket:latest,NEXUS_BACKEND=northstar-dev-nexus-backend:latest
