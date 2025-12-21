from __future__ import annotations

from engines.common.identity import RequestContext
from engines.nexus.vector_explorer.schemas import VectorExplorerQuery
from engines.nexus.vector_explorer.service import VectorExplorerService
from engines.nexus.vector_explorer.repository import InMemoryVectorCorpusRepository
from engines.nexus.vector_explorer.vector_store import ExplorerVectorStore, ExplorerVectorHit
from engines.nexus.embedding import EmbeddingAdapter, EmbeddingResult
from engines.budget.repository import InMemoryBudgetUsageRepository
from engines.budget.service import BudgetService, set_budget_service


class FakeEmbedder(EmbeddingAdapter):
    def embed_text(self, text: str, model_id=None, context=None) -> EmbeddingResult:
        return EmbeddingResult(vector=[1.0, 0.0], model_id="text-model")

    def embed_image(self, image_uri: str, model_id=None, context=None) -> EmbeddingResult:  # pragma: no cover - unused
        return EmbeddingResult(vector=[0.0, 1.0], model_id="image-model")

    def embed_image_bytes(self, image_bytes: bytes, model_id=None, context=None) -> EmbeddingResult:  # pragma: no cover - unused
        return EmbeddingResult(vector=[0.0, 1.0], model_id="image-model")


class FakeVectorStore(ExplorerVectorStore):
    def query(self, vector, tenant_id, env, space, top_k=10):
        return [ExplorerVectorHit(id="doc1", score=0.9, metadata={})]

    def query_by_datapoint_id(self, anchor_id, tenant_id, env, space, top_k=10):
        return []

    def upsert(self, item_id, vector, tenant_id, env, space, metadata=None):  # pragma: no cover - unused
        return None


def test_usage_record_written_on_similar_text_query():
    usage_repo = InMemoryBudgetUsageRepository()
    set_budget_service(BudgetService(repo=usage_repo))
    svc = VectorExplorerService(
        repository=InMemoryVectorCorpusRepository(),
        vector_store=FakeVectorStore(),
        embedder=FakeEmbedder(),
        event_logger=None,
    )
    q = VectorExplorerQuery(tenant_id="t_test", env="dev", space="s", query_mode="similar_to_text", query_text="hello")
    svc.build_scene_from_query(q)
    events = usage_repo.list_usage(tenant_id="t_test", env="dev")
    assert events
    rec = events[0]
    assert rec.surface == "vector_explorer"
