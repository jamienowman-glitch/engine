# ENGINES LOCAL DEV RUN (VECTOR EXPLORER + CHAT SERVER)

This is the canonical local bring-up for the engines backend exposing `/vector-explorer/ingest` and `/vector-explorer/scene`.

## One-time setup
```bash
cd /Users/jaynowman/dev/northstar-engines
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
gcloud auth application-default login
```

## Every time (run the backend)
```bash
cd /Users/jaynowman/dev/northstar-engines
source .venv/bin/activate
export TENANT_ID=t_northstar-dev
export ENV=dev
export RAW_BUCKET=gs://northstar-os-dev-northstar-raw
export DATASETS_BUCKET=gs://northstar-os-dev-northstar-datasets
export GCP_PROJECT_ID=northstar-os-dev
export GCP_REGION=us-central1
export VECTOR_PROJECT_ID=$GCP_PROJECT_ID
export VECTOR_ENDPOINT_ID=<vertex_endpoint_id_from_northstar_os_dev>
export VECTOR_INDEX_ID=<vertex_index_id_from_northstar_os_dev>
export TEXT_EMBED_MODEL=text-embedding-004
export IMAGE_EMBED_MODEL=multimodalembedding@001
uvicorn engines.chat.service.server:app --host 0.0.0.0 --port 8000
```

## Create Vertex index & endpoint (dev, us-central1, project northstar-os-dev)
Run once (after you prepare an `index_config.json` that matches your embedding dims/metric):
```bash
gcloud config set project northstar-os-dev
gcloud config set ai/region us-central1

gcloud ai indexes create \
  --display-name=haze-vector-index-dev \
  --description="Haze vector index (dev)" \
  --metadata-file=index_config.json

gcloud ai index-endpoints create \
  --display-name=haze-vector-endpoint-dev

gcloud ai index-endpoints deploy-index \
  --index-endpoint=<INDEX_ENDPOINT_ID_FROM_STEP_2> \
  --index=<INDEX_ID_FROM_STEP_1> \
  --deployed-index-id=haze-vector-deployed-dev \
  --display-name=haze-vector-deployed-dev

gcloud ai indexes list --format="value(name)"
gcloud ai index-endpoints list --format="value(name)"
```
After running, paste the returned IDs into `VECTOR_INDEX_ID` and `VECTOR_ENDPOINT_ID` above.

## Notes
- Routes `/vector-explorer/ingest` and `/vector-explorer/scene` are served by the chat server app.
- ADC (Application Default Credentials) is expected; ensure your gcloud account has access to Firestore, GCS, and Vertex in `northstar-os-dev`. If using a service account key, set `GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json` before running.
- Corpus collection: `vector_corpus_<TENANT_ID>` in Firestore; media stored under `gs://${RAW_BUCKET}/${TENANT_ID}/media/...`; vector restricts include tenant/env/space.
