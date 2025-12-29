# ENGINES DEV RUNTIME (PLAN-026)

Dev runtime expectations for `northstar-os-dev` on Cloud Run.

- Project: `northstar-os-dev`
- Region: `us-central1`
- Service Account: `northstar-dev-engines@northstar-os-dev.iam.gserviceaccount.com`
- Auth: Application Default Credentials; no API keys.
- Env vars (wired via Cloud Run / GSM):
  - `TENANT_ID` (e.g., `t_northstar-dev`)
  - `RAW_BUCKET` (`gs://northstar-os-dev-northstar-raw`)
  - `DATASETS_BUCKET` (`gs://northstar-os-dev-northstar-datasets`)
  - `NEXUS_BACKEND` (`firestore`)
  - `GCP_PROJECT_ID` (`northstar-os-dev`)
  - `GCP_REGION` (`us-central1`)
- Services expected:
  - Firestore (Native) for Nexus (snippets/events/plans).
  - GCS for media ingest and datasets.
  - Vertex AI (Gemini) for chat orchestration.
- Entrypoint: `uvicorn engines.chat.service.server:app --host 0.0.0.0 --port 8000`
- Media endpoints: `POST /media/upload` (multipart), `GET /media/stack`.
- Chat endpoints: `/chat/threads`, `/chat/threads/{id}/messages`, WS/SSE for streaming.
