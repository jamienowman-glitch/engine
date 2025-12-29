# CONNECTORS HANDOFF (northstar-engines → connectors repo)

This is the handoff for building MCP connectors (Google/AWS/etc.) in a separate repo without drifting from the engines layer. It restates existing contracts only; do not change any naming/tenant semantics.

## Non-negotiables (must not change)
- `tenant_id` format: `t_<slug>` (lowercase, alphanumeric plus `-`/`_`), e.g. `t_northstar-dev`.
- `connector_id` format: `conn.<provider>.<product>.<scope>` (provider=cloud/vendor, product=service family, scope=lane such as core/chat/eval/ingest).
- GSM secret patterns (no new patterns):
  - OS-paid: `conn-<provider>-<product>-<scope>-key` (suffix `-refresh`/`-secret` only when already used).
  - BYOK per tenant: `tenant-<tenant_id>-<provider>-<product>-<scope>-key` (same suffix rules).
- Existing GSM names used in dev must stay stable: `northstar-dev-tenant-0-id`, `northstar-dev-raw-bucket`, `northstar-dev-datasets-bucket`, `northstar-dev-nexus-backend`, `auth-jwt-secret`.
- Tenant IDs are always passed in/contextual (never hard-coded), and Nexus/vector metadata must carry `tenant_id` + `env`.

## Env and secret inputs connectors must honor
- Identity/tenant/env: `TENANT_ID`, `ENV` or `APP_ENV`.
- Nexus backend selection: `NEXUS_BACKEND` (engines enforce `firestore`; raise if different).
- Buckets: `RAW_BUCKET`, `DATASETS_BUCKET` (used for media + dataset paths).
- GCP coordinates: `GCP_PROJECT_ID`/`GCP_PROJECT`, `GCP_REGION`/`REGION` (default `us-central1`), `VECTOR_PROJECT_ID` (optional override for vector).
- Vector config: `VECTOR_INDEX_ID` or `VERTEX_VECTOR_INDEX_ID`; `VECTOR_ENDPOINT_ID` or `VERTEX_VECTOR_ENDPOINT_ID`.
- Model config:
  - Chat: `VERTEX_MODEL` (default `gemini-1.5-flash-002`).
  - Embeddings: `TEXT_EMBED_MODEL`/`VERTEX_TEXT_EMBED_MODEL`; `IMAGE_EMBED_MODEL`/`VERTEX_IMAGE_EMBED_MODEL`.
  - Eval/backends: `VERTEX_EVAL_MODEL_ID`, `BEDROCK_EVAL_MODEL_ID`, `RAGAS_EVAL_URL`, `RAGAS_EVAL_TOKEN`.
  - Forecasting: `VERTEX_FORECAST_DATASET`, `VERTEX_FORECAST_TABLE`, `BQ_ML_FORECAST_DATASET`, `BQ_ML_FORECAST_TABLE`, `AWS_FORECAST_ROLE_ARN`, `AWS_FORECAST_DATASET_GROUP`.
- Security/billing tokens surfaced as env names (values expected from GSM or equivalent): `GHAS_APP_ID`, `GHAS_PRIVATE_KEY_SECRET`, `DEPENDABOT_TOKEN_SECRET`, `SEMGREP_TOKEN_SECRET`, `SONAR_TOKEN_SECRET`, `IMAGEN_API_KEY_SECRET`, `NOVA_API_KEY_SECRET`, `BRAKET_ROLE_ARN`, `BRAKET_REGION`.
- JWT signing secret lives in GSM as `auth-jwt-secret`; never in env.

## Current GCP dev baseline (do not drift)
- Project: `northstar-os-dev`; Region: `us-central1`; Service account: `northstar-dev-engines@northstar-os-dev.iam.gserviceaccount.com` with roles `secretmanager.secretAccessor`, `storage.objectAdmin`, `run.invoker`, `aiplatform.user`.
- Buckets: `gs://northstar-os-dev-northstar-raw` (raw uploads), `gs://northstar-os-dev-northstar-datasets` (datasets).
- Nexus backend: Firestore Native in `us-central1`; Nexus backend name is read from GSM `northstar-dev-nexus-backend` and must stay `firestore`.
- Secrets resolved via Cloud Run `--update-secrets`: `TENANT_ID=northstar-dev-tenant-0-id`, `RAW_BUCKET=northstar-dev-raw-bucket`, `DATASETS_BUCKET=northstar-dev-datasets-bucket`, `NEXUS_BACKEND=northstar-dev-nexus-backend`.
- Authentication to GCP is ADC only; no API keys in env. Connectors must keep this posture.

## Nexus + media expectations (current engine contracts)
- Backend factory refuses anything except Firestore (`NEXUS_BACKEND`), so connector glue must provide Firestore access in the configured `GCP_PROJECT_ID`/`REGION`.
- Firestore collection naming:
  - Snippets: `nexus_snippets_{tenant_id}`; Events: `nexus_events_{tenant_id}`.
  - Plans: `{kind}_plans_{tenant_id}` with versioned docs (used by temperature plans, etc.).
- Stored metadata includes `tenant_id` + `env`; callers pass `tenant_id` explicitly (runtime default from env is allowed but not hard-coded).
- Media endpoints write raw files to `RAW_BUCKET` under `<tenant_id>/media/<uuid>/<filename>` and store a Nexus snippet tagged `media`; listing reads Nexus by `tags=["media"]`. Keep this path shape.

## Vector explorer + vector store wiring (today)
- Corpus repository is Firestore collection `vector_corpus_{tenant_id}` with fields `{id, tenant_id, env, space, label, tags[], metrics{}, vector_ref, source_ref, created_at}`; filters require `env` + `space` and optional tags/metadata equality.
- Vector backend is Vertex Matching Engine:
  - Requires `VECTOR_PROJECT_ID` (or `GCP_PROJECT_ID`), `GCP_REGION/REGION` (default `us-central1`), `VECTOR_ENDPOINT_ID`, and `VECTOR_INDEX_ID` (deployed index id inferred from endpoint if not provided).
  - Upserts set restricts on namespaces `tenant_id`, `env`, `space`; queries enforce the same. Tenant/env scoping is mandatory.
  - Embeddings use Vertex models from env (`TEXT_EMBED_MODEL` / `IMAGE_EMBED_MODEL`) via ADC.
- Scene building uses recipe `vector_space_explorer`; HTTP route `/vector-explorer/scene` accepts `tenant_id`, `env`, `space`, `query_mode (all|similar_to_id|similar_to_text)`, `tags`, `anchor_id`, `query_text`, `limit`. DatasetEvents are emitted for queries and scene composition.
- Vector ingest service (production path) expects real embeddings + vector upsert; it fails if vector config is missing and logs DatasetEvents `vector_ingest.*`. Storage for binaries uses `RAW_BUCKET` via `GcsClient`.

## BYOK and secret handling expectations
- BYOK API shape (planning, to preserve): `POST /tenants/{tenant_id}/connectors/{provider}/{product}/{scope}/key` body `{ "api_key": "<secret>" }` → store in GSM as `tenant-<tenant_id>-<provider>-<product>-<scope>-key`; metadata only in DB (`has_byok`, `last_updated_at`, `masked_preview`). `GET /tenants/{tenant_id}/connectors` returns metadata only.
- OS-paid lanes read `conn-<provider>-<product>-<scope>-key`; no raw secrets in logs/Nexus/DatasetEvents; apply PII/redaction on request/response logging.
- Tenant/env/bucket coordinates are non-secret env vars; do not move them to plaintext secrets. Keep raw keys solely in GSM.

## What should move into connectors (keep contracts)
- SDK/client calls currently in engines that should be relocated behind connector adapters without changing behavior:
  - Vertex AI chat streaming (`engines/chat/service/llm_client.py`) using ADC, `GCP_PROJECT_ID`, `GCP_REGION`, `VERTEX_MODEL`.
  - Vertex embeddings + Matching Engine (`engines/nexus/embedding.py`, `engines/nexus/vector_explorer/vector_store.py`, `engines/nexus/vector_explorer/vertex_search.py`) using env-configured project/region/index/endpoint/model IDs with tenant/env/space filters.
  - Firestore access for Nexus and vector corpus (`engines/nexus/backends/firestore_backend.py`, `engines/nexus/vector_explorer/repository.py`).
  - GCS writes for media/vector ingest (`engines/storage/gcs_client.py`) using `RAW_BUCKET`/`DATASETS_BUCKET`.
  - Any future AWS clients for Bedrock evals (`BEDROCK_EVAL_MODEL_ID`) and Forecast (`AWS_FORECAST_ROLE_ARN`, `AWS_FORECAST_DATASET_GROUP`) should be provided by connectors but retain the same env variable names.
- Request/response shapes to preserve:
  - Chat pipeline emits DatasetEvents with `tenant_id`, `env`, `surface="chat"`, `agentId` from sender; history is streamed to the LLM client; keep the SSE/WS-friendly stream interface.
  - Vector explorer route and ingest route parameter shapes above; include tenant/env/space/query metadata in any connector calls.
- Connectors should derive GSM secret names from `connector_id` + optional `tenant_id` using the locked patterns; never invent alternates.

## Guardrails against drift
- Do not rename env vars, bucket paths, or GSM names. Connectors may add provider-specific details internally but must keep the public contract identical.
- Always include `tenant_id` and `env` when writing to Firestore, GCS paths, Nexus, vector metadata, or DatasetEvents.
- If a secret/config is missing, fail loudly (current code raises `VectorStoreConfigError`/`RuntimeError`); do not silently fall back to memory or stubbed endpoints.
