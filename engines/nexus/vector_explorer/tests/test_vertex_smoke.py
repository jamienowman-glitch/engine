import os
import uuid

import pytest

from engines.nexus.embedding import VertexEmbeddingAdapter
from engines.nexus.vector_explorer.vector_store import VertexExplorerVectorStore, VectorStoreConfigError


REQUIRED_ENV = [
    "GCP_PROJECT_ID",
    "GCP_REGION",
    "VECTOR_INDEX_ID",
    "VECTOR_ENDPOINT_ID",
    "TEXT_EMBED_MODEL",
]


def _env_ready() -> bool:
    return all(os.getenv(k) for k in REQUIRED_ENV)


@pytest.mark.skipif(not _env_ready(), reason="Vertex env vars not set; skipping smoke test")
def test_vertex_smoke_upsert_and_query():
    adapter = VertexEmbeddingAdapter()
    embed = adapter.embed_text("vertex smoke test")
    store = VertexExplorerVectorStore()
    item_id = uuid.uuid4().hex
    tenant = os.getenv("TENANT_ID", "t_smoke")
    env = os.getenv("ENV", "dev")
    space = "haze-default"

    # upsert should not raise
    store.upsert(
        item_id=item_id,
        vector=embed.vector,
        tenant_id=tenant,
        env=env,
        space=space,
        metadata={"test": True},
    )

    # query should return without InvalidArgument
    try:
        store.query(vector=embed.vector, tenant_id=tenant, env=env, space=space, top_k=1)
    except VectorStoreConfigError as exc:
        pytest.fail(f"Vector query failed: {exc}")
