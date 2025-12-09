This file is the only canonical source of truth for dev infra for northstar-engines.
All agents (Max, Gem, Claude, etc.) must read from here and must not invent new project IDs, service accounts, buckets, or secret names.

---

# GCP Infrastructure Baseline (Dev)

- **Project**: `northstar-os-dev`
- **Region**: `us-central1`

---

## Service Accounts & Roles

- **Engines Service Account (dev)**:
    - `northstar-dev-engines@northstar-os-dev.iam.gserviceaccount.com`
- **Required Roles on this Service Account**:
    - `roles/secretmanager.secretAccessor`
    - `roles/storage.objectAdmin`
    - `roles/run.invoker`
    - `roles/aiplatform.user`

---

## Backends & Storage

- **Nexus Backend (dev)**:
    - `firestore` (Native mode, us-central1)
- **GCS Buckets (dev)**:
    - **Raw Uploads**: `gs://northstar-os-dev-northstar-raw`
    - **Datasets**: `gs://northstar-os-dev-northstar-datasets`

---

## Secrets (Google Secret Manager)

- **Tenant 0 ID**:
    - **Name**: `northstar-dev-tenant-0-id`
    - **Value**: `t_northstar-dev`
- **Raw Bucket**:
    - **Name**: `northstar-dev-raw-bucket`
    - **Value**: `gs://northstar-os-dev-northstar-raw`
- **Datasets Bucket**:
    - **Name**: `northstar-dev-datasets-bucket`
    - **Value**: `gs://northstar-os-dev-northstar-datasets`
- **Nexus Backend**:
    - **Name**: `northstar-dev-nexus-backend`
    - **Value**: `firestore`
