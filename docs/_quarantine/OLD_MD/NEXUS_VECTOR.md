# NEXUS VECTOR ENABLEMENT (PLANNING)

Goal: add vector search to Nexus with minimal cost, keeping Firestore as the source of truth and making vectors accessible to all agents.

## Recommended stack (GCP-first)
- Vector index: Vertex AI Vector Search (us-central1). Alternatives: BigQuery vectors (cheap, slower), self-hosted pgvector/Weaviate (more ops), AWS Bedrock Kendra/Opensearch if running in AWS.
- Embeddings:
  - Text: Vertex `text-embedding` (Gecko or latest) for snippets/plans/chat.
  - Image/style: Vertex multimodal/image embedding for aesthetic/style signals (fallback to OSS CLIP if cost-sensitive).
- Storage of records: Firestore remains canonical; vectors hold `{id, tenant_id, env, kind, embedding, metadata, refs}`.

## Index design (Vertex)
- Dimensions: match embedding model (e.g., 768 for Gecko). Use a single index with metadata filters on `tenant_id`, `env`, `kind` (style, content, plan, chat).
- Endpoint: one per environment (dev/prod). Auto-scaling min=0 to save credits.
- Metadata fields: `tenant_id`, `env`, `kind`, `created_at`, `source_ref` (nexus doc id), optional `tags`.

## Pipeline changes (minimal)
- On write to Firestore (snippets/events/plans):
  1) Build text payload (or image URL) for embedding.
  2) Call embedding model.
  3) Upsert `{id, embedding, metadata}` into the vector index.
- On query:
  1) Embed the query text/image.
  2) Query index with filters (`tenant_id`, `env`, `kind`).
  3) Return top K refs → fetch full docs from Firestore.
- Keep ingestion async (queue/batch) to reduce latency/cost.

## Style / aesthetic nexus
- Separate `kind="style"` docs: user/style boards, taste tags, asset refs, palette descriptors.
- Text embedding for descriptions; image embedding for inspiration assets.
- Agents query with both: “style: bold minimal, palette: cobalt/cream” → vector search over `kind=style`, `tenant_id`, `env`.

## Config/ENV to add
- `VECTOR_BACKEND=vertex`
- `VECTOR_INDEX_ID` and `VECTOR_ENDPOINT_ID` per env.
- `EMBED_MODEL_TEXT` (e.g., `text-embedding-gecko`), `EMBED_MODEL_IMAGE` (if used).
- `VECTOR_DIM` (e.g., 768).

## Cost controls
- Auto-scaling min=0 on endpoints; small shard count.
- Batch upserts; low-frequency re-embedding.
- Keep index per env; prune stale vectors.
- Prefer text-only embeddings unless style/image needed.

## Rough steps to turn on (when ready)
1) Enable `aiplatform.googleapis.com`; create Vertex index (us-central1) with correct dim + metadata filtering.
2) Deploy index endpoint; note INDEX_ID/ENDPOINT_ID.
3) Wire env vars/secrets above into engines.
4) Add embed→upsert hook in Nexus backend; async preferred.
5) Add query helper that embeds + filters (tenant/env/kind) and returns Firestore docs.
6) Seed a small corpus (style + content) to smoke-test recall.***
