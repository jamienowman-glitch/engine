from __future__ import annotations

from engines.nexus.embedding import EmbeddingResult, EmbeddingAdapter
from engines.budget.repository import InMemoryBudgetUsageRepository
from engines.budget.service import BudgetService
from engines.nexus.vector_explorer.repository import InMemoryVectorCorpusRepository
from engines.nexus.vector_explorer.schemas import QueryMode, VectorExplorerItem, VectorExplorerQuery
from engines.nexus.vector_explorer.service import VectorExplorerService
from engines.nexus.vector_explorer.vector_store import ExplorerVectorHit, ExplorerVectorStore


class FakeEmbedder(EmbeddingAdapter):
    def embed_text(self, text: str, model_id=None) -> EmbeddingResult:
        return EmbeddingResult(vector=[1.0, 0.0], model_id="text-model")

    def embed_image(self, image_uri: str, model_id=None) -> EmbeddingResult:  # pragma: no cover - unused
        return EmbeddingResult(vector=[0.0, 1.0], model_id="image-model")

    def embed_image_bytes(self, image_bytes: bytes, model_id=None) -> EmbeddingResult:  # pragma: no cover - unused
        return EmbeddingResult(vector=[0.0, 1.0], model_id="image-model")


class FakeVectorStore(ExplorerVectorStore):
    def __init__(self):
        self.vectors = {}

    def upsert(self, item_id, vector, tenant_id, env, space, metadata=None):
        self.vectors[item_id] = list(vector)

    def query(self, vector, tenant_id, env, space, top_k=10):
        return [ExplorerVectorHit(id=item_id, score=1.0, metadata={}) for item_id in self.vectors][:top_k]

    def query_by_datapoint_id(self, anchor_id, tenant_id, env, space, top_k=10):
        return [ExplorerVectorHit(id=item_id, score=1.0, metadata={}) for item_id in self.vectors][:top_k]


def test_query_all_and_scene_builds():
    repo = InMemoryVectorCorpusRepository(
        [
        VectorExplorerItem(id="a", label="Alpha", tags=["x"], metrics={}, source_ref={"uri": "s1"}),
        VectorExplorerItem(id="b", label="Beta", tags=["y"], metrics={}, source_ref={"uri": "s2"}, height_score=0.7),
    ]
    )
    events = []
    svc = VectorExplorerService(
        repository=repo,
        vector_store=FakeVectorStore(),
        embedder=FakeEmbedder(),
        event_logger=lambda e: events.append(e),
        budget_service=BudgetService(repo=InMemoryBudgetUsageRepository()),
    )
    query = VectorExplorerQuery(tenant_id="t_demo", env="dev", space="demo", query_mode=QueryMode.all, limit=10)
    result = svc.query_items(query)
    assert len(result.items) == 2
    scene = svc.build_scene_from_query(query)
    assert scene.nodes and len(scene.nodes) == 2
    assert events and events[0].metadata.get("kind") == "vector_explorer.query"


def test_similar_to_id_hydrates_scores():
    repo = InMemoryVectorCorpusRepository(
        [
            VectorExplorerItem(id="anchor", label="Anchor", tags=[], metrics={}, source_ref={}),
            VectorExplorerItem(id="peer", label="Peer", tags=[], metrics={}, source_ref={}),
        ]
    )
    store = FakeVectorStore()
    store.vectors = {"peer": [1.0, 0.0]}
    svc = VectorExplorerService(
        repository=repo,
        vector_store=store,
        embedder=FakeEmbedder(),
        event_logger=lambda e: None,
        budget_service=BudgetService(repo=InMemoryBudgetUsageRepository()),
    )
    query = VectorExplorerQuery(
        tenant_id="t_demo", env="dev", space="demo", query_mode=QueryMode.similar_to_id, anchor_id="anchor"
    )
    result = svc.query_items(query)
    assert result.items
    assert result.items[0].similarity_score is not None
