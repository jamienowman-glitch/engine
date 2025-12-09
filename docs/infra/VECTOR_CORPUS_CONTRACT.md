# VECTOR CORPUS CONTRACT (PLAN-0AI-P0)

Corpus records live in Firestore; embeddings are stored in the configured vector backend (e.g., Vertex Matching Engine) keyed by `id`. Ingestion/embedding occurs outside this repo (console/notebook/manual).

## Firestore shape
- Collection: `vector_corpus_<tenant_id>`
- Document fields:
  - `id` (string, doc_id)
  - `tenant_id` (t_* pattern)
  - `env` (dev/stage/prod)
  - `space` (string; maps to vector namespace/kind)
  - `label` (short display label)
  - `tags` (array of strings)
  - `metrics` (map; numeric scores, may include `size_hint`)
  - `vector_ref` (string map to vector backend id/namespace; optional)
  - `source_ref` (map; e.g., {source_uri, card_ref, nexus_ref})
  - `created_at` (timestamp)

## Expectations
- No LLM calls in this pipeline; vector backend is infra like Firestore/GCS.
- Vector backend config comes from existing env getters (VECTOR_INDEX_ID, VECTOR_ENDPOINT_ID, VECTOR_PROJECT_ID, TEXT_EMBED_MODEL, IMAGE_EMBED_MODEL).
- Hydration reads Firestore docs by id/tag filters; similarity search uses vector backend when configured, otherwise falls back to Firestore-only listing (query_mode="all").

## Out of scope
- No ingestion or embedding code in this repo.
- No UI or orchestration dependencies. Scene Engine is the only downstream consumer in this plan.
