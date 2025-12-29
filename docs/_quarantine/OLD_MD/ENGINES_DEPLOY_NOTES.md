# Engines Deployment Notes

## Scene Engine (Cloud Run stub)
- Image: `gcr.io/PROJECT_ID/scene-engine:latest`
- Port: `8080`
- Env: `PORT` (default 8080)
- Deploy manifest: `engines/scene_engine/deploy/cloudrun.yaml`

Assumptions: Cloud Run default service account; adjust `PROJECT_ID` and add IAM/ingress as needed before deployment.
