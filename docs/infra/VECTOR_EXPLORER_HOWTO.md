# VECTOR EXPLORER HOWTO (PLAN-0AI-P4)

Purpose: serve vector corpus slices into 3D scenes (Scene Engine) without LLM/orchestration dependencies.

## Setup
1) Ensure env vars/secrets for vector backend are set (per NEXUS vector enablement):
   - `VECTOR_PROJECT_ID`/`GCP_PROJECT_ID`
   - `VECTOR_INDEX_ID`, `VECTOR_ENDPOINT_ID`
   - `TEXT_EMBED_MODEL` (for similar_to_text)
2) Create Firestore collection `vector_corpus_<tenant_id>` and add documents following `docs/infra/VECTOR_CORPUS_CONTRACT.md`.
   - Embeddings must already be indexed in the vector backend under the same `id` and `space`.

## Using the API
- Endpoint: `GET /vector-explorer/scene`
- Params: `tenant_id`, `env`, `space`, `query_mode` (`all|similar_to_id|similar_to_text`), `limit` (default 20), optional `tags` (comma-separated), `query_text`, `anchor_id` (for similar_to_id).
- Response: Scene JSON compatible with Scene Engine (`scene.nodes[]` with meta carrying tags/metrics/similarity/source_ref).

## Logging
- DatasetEvents emitted for queries and scene composition (`vector_explorer.query`, `vector_explorer.scene_composed`) with tenant/env/trace_id and item ids.

## Notes
- No ingestion/embedding code here; manage corpus and embeddings externally.
- No LLM/agent runtime imports; vector backend + Firestore only.
