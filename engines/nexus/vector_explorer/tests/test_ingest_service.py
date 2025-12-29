from __future__ import annotations

from engines.budget.repository import InMemoryBudgetUsageRepository
from engines.budget.service import BudgetService
from engines.nexus.embedding import EmbeddingResult, EmbeddingAdapter
from engines.nexus.vector_explorer.ingest_service import VectorIngestService
from engines.nexus.vector_explorer.repository import InMemoryVectorCorpusRepository
from engines.nexus.vector_explorer.vector_store import ExplorerVectorStore, ExplorerVectorHit


class FakeEmbedder(EmbeddingAdapter):
    def embed_text(self, text: str, model_id=None, context=None) -> EmbeddingResult:
        return EmbeddingResult(vector=[0.5, 0.5], model_id="text-model")

    def embed_image(self, image_uri: str, model_id=None, context=None) -> EmbeddingResult:  # pragma: no cover - unused
        return EmbeddingResult(vector=[1.0, 0.0], model_id="image-model")

    def embed_image_bytes(self, image_bytes: bytes, model_id=None, context=None) -> EmbeddingResult:
        return EmbeddingResult(vector=[1.0, 0.0], model_id="image-model")


class FakeVectorStore(ExplorerVectorStore):
    def __init__(self):
        self.upserts = []

    def upsert(self, item_id, vector, tenant_id, env, space, metadata=None):
        self.upserts.append((item_id, vector, tenant_id, env, space, metadata))

    def query(self, vector, tenant_id, env, space, top_k=10):
        return [ExplorerVectorHit(id=u[0], score=1.0, metadata={}) for u in self.upserts]

    def query_by_datapoint_id(self, anchor_id, tenant_id, env, space, top_k=10):
        return [ExplorerVectorHit(id=u[0], score=1.0, metadata={}) for u in self.upserts]


class FakeGcs:
    def __init__(self):
        self.uploads = []

    def upload_raw_media(self, tenant_id, path, content):
        self.uploads.append((tenant_id, path))
        return f"gs://bucket/{tenant_id}/{path}"


def test_ingest_text_creates_corpus_and_vector():
    repo = InMemoryVectorCorpusRepository()
    store = FakeVectorStore()
    svc = VectorIngestService(
        corpus_repo=repo,
        vector_store=store,
        embedder=FakeEmbedder(),
        gcs_client=FakeGcs(),
        event_logger=lambda e: None,
        budget_service=BudgetService(repo=InMemoryBudgetUsageRepository()),
    )
    result = svc.ingest(
        tenant_id="t_demo",
        env="dev",
        space="demo",
        content_type="text",
        label="hello",
        tags=["tag1"],
        text_content="sample text",
        file_bytes=None,
        filename=None,
    )
    assert result.item.id in repo._items  # type: ignore[attr-defined]
    assert store.upserts, "expected vector upsert"


def test_ingest_image_requires_file():
    repo = InMemoryVectorCorpusRepository()
    store = FakeVectorStore()
    svc = VectorIngestService(
        corpus_repo=repo,
        vector_store=store,
        embedder=FakeEmbedder(),
        gcs_client=FakeGcs(),
        event_logger=lambda e: None,
        budget_service=BudgetService(repo=InMemoryBudgetUsageRepository()),
    )
    result = svc.ingest(
        tenant_id="t_demo",
        env="dev",
        space="demo",
        content_type="image",
        label="img",
        tags=[],
        text_content="",
        file_bytes=b"\x89PNG",
        filename="img.png",
    )
    assert result.gcs_uri and result.item.id in repo._items  # type: ignore[attr-defined]
