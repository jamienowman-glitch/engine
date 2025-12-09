# VECTOR EXPLORER DEV RUN (HAZE) – BACKEND BRING-UP

Use this as the single reference to run the vector ingest + scene endpoints locally against real Firestore + Vertex.

## Start command (serves ingest + scene)
```bash
uvicorn engines.chat.service.server:app --host 0.0.0.0 --port 8000
```
- The chat server aggregates the vector explorer routes: `/vector-explorer/ingest`, `/vector-explorer/scene`.
- Bind `--host 0.0.0.0` to reach from LAN; choose any `--port` (8000 used here).
- Dependencies: ensure `google-cloud-aiplatform` and `python-multipart` are installed (included in requirements.txt).

## Required env vars
- `TENANT_ID` (e.g., `t_northstar-dev`)
- `ENV` or `APP_ENV` (e.g., `dev`)
- `RAW_BUCKET` (GCS bucket for media uploads, e.g., `northstar-os-dev-northstar-raw`)
- `DATASETS_BUCKET` (optional; not required for vector explorer but used elsewhere)
- `GCP_PROJECT_ID` (Firestore/Vertex project, e.g., `northstar-os-dev`)
- `GCP_REGION` (e.g., `us-central1`)
- `VECTOR_PROJECT_ID` (optional override; defaults to `GCP_PROJECT_ID`)
- `VECTOR_INDEX_ID` (Vertex Matching Engine **index** resource name or ID used for upserts)
- `VECTOR_ENDPOINT_ID` (Vertex Matching Engine **endpoint** resource name or ID used for queries)
- `TEXT_EMBED_MODEL` (Vertex text embedding model ID)
- `IMAGE_EMBED_MODEL` (Vertex multimodal/image embedding model ID)

### Create Vertex index & endpoint (dev, us-central1, project northstar-os-dev)
Run once to create the index + endpoint (replace names if you prefer):
```bash
gcloud config set project northstar-os-dev
gcloud config set ai/region us-central1

# 1) Create the index (haze-vector-index-dev)
gcloud ai indexes create \
  --display-name=haze-vector-index-dev \
  --description="Haze vector index (dev)" \
  --metadata-file=index_config.json

# 2) Create endpoint (haze-vector-endpoint-dev)
gcloud ai index-endpoints create \
  --display-name=haze-vector-endpoint-dev

# 3) Deploy the index to the endpoint
gcloud ai index-endpoints deploy-index \
  --index-endpoint=<INDEX_ENDPOINT_ID_FROM_STEP_2> \
  --index=<INDEX_ID_FROM_STEP_1> \
  --deployed-index-id=haze-vector-deployed-dev \
  --display-name=haze-vector-deployed-dev

# 4) Retrieve IDs
gcloud ai indexes list --format="value(name)"
gcloud ai index-endpoints list --format="value(name)"
```
Notes:
- `index_config.json` should define dimensions/metric per your embedding model (see Vertex docs for Matching Engine index metadata). Supply it before running the create command.
- After running, set `VECTOR_INDEX_ID` to the returned index ID and `VECTOR_ENDPOINT_ID` to the index endpoint ID.

### ENV EXPORTS (DEV)
```bash
export TENANT_ID=t_northstar-dev
export ENV=dev
export RAW_BUCKET=gs://northstar-os-dev-northstar-raw
export DATASETS_BUCKET=gs://northstar-os-dev-northstar-datasets
export GCP_PROJECT_ID=northstar-os-dev
export GCP_REGION=us-central1
export VECTOR_PROJECT_ID=$GCP_PROJECT_ID

# RESOURCE IDs: You can use full resource names (projects/.../indexes/123) OR bare IDs (123).
export VECTOR_INDEX_ID=<INSERT_REAL_INDEX_ID_HERE>          
export VECTOR_ENDPOINT_ID=<INSERT_REAL_ENDPOINT_ID_HERE>    

export TEXT_EMBED_MODEL=text-embedding-004
export IMAGE_EMBED_MODEL=multimodalembedding@001
```

## Common 400 errors (Vertex)
- `Request contains an invalid argument`: 
    - Often means `VECTOR_INDEX_ID` or `VECTOR_ENDPOINT_ID` don't point to valid resources in the project/region.
    - Can also mean the Endpoint does not have the Index deployed to it. **Crucial**: The code requires `VECTOR_ENDPOINT_ID` to be an Endpoint that has a `deployed_index`.
- `Vertex upsert failed`: 
    - Check if `VECTOR_INDEX_ID` matches the index you intend to write to.
- `Vertex query failed`: 
    - Check if `VECTOR_ENDPOINT_ID` has a deployed index.
- Embedding dimension mismatch: 
    - Index must be created with dimensions matching `text-embedding-004` (768). Recreate index if dimensions differ.
- Permission/auth issues: confirm ADC/service account has Vertex AI permissions.

### Auth
- Application Default Credentials must be active (`gcloud auth application-default login`) with access to Firestore, GCS, and Vertex Matching Engine.

## Smoke test (curl)
Ingest text:
```bash
curl -X POST http://localhost:8000/vector-explorer/ingest \
  -F tenant_id=${TENANT_ID} \
  -F env=${ENV:-dev} \
  -F space=haze-default \
  -F content_type=text \
  -F label="hello haze" \
  -F text_content="sample text for haze"
```

Fetch scene:
```bash
curl "http://localhost:8000/vector-explorer/scene?tenant_id=${TENANT_ID}&env=${ENV:-dev}&space=haze-default&query_mode=all&limit=50"
```

## Collections / vector
- Corpus collection: `vector_corpus_<tenant_id>` in Firestore (Native).
- Media stored in `gs://${RAW_BUCKET}/${tenant_id}/media/<asset_id>/...`.
- Vector restricts: `tenant_id`, `env`, `space` (namespace is `space`).

## Failure modes
- Missing vector config or Vertex client errors → HTTP 500.
- Missing required form fields → HTTP 400.
- No in-memory/demo fallbacks; real Firestore + Vertex are required.
