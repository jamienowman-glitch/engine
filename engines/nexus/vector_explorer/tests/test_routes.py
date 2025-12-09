from __future__ import annotations

from fastapi.testclient import TestClient

from engines.chat.service.server import create_app
from engines.nexus.vector_explorer import routes
from engines.nexus.vector_explorer.repository import InMemoryVectorCorpusRepository
from engines.nexus.vector_explorer.schemas import VectorExplorerItem
from engines.nexus.vector_explorer.service import VectorExplorerService
from engines.nexus.vector_explorer.vector_store import ExplorerVectorStore, ExplorerVectorHit
from engines.nexus.embedding import EmbeddingAdapter, EmbeddingResult


def test_vector_explorer_route(monkeypatch):
    class FakeEmbedder(EmbeddingAdapter):
        def embed_text(self, text: str, model_id=None) -> EmbeddingResult:
            return EmbeddingResult(vector=[1.0, 0.0], model_id="text")

        def embed_image(self, image_uri: str, model_id=None) -> EmbeddingResult:  # pragma: no cover - unused
            return EmbeddingResult(vector=[0.0, 1.0], model_id="image")

        def embed_image_bytes(self, image_bytes: bytes, model_id=None) -> EmbeddingResult:  # pragma: no cover - unused
            return EmbeddingResult(vector=[0.0, 1.0], model_id="image")

    class FakeVectorStore(ExplorerVectorStore):
        def query(self, vector, tenant_id, env, space, top_k=10):
            return [ExplorerVectorHit(id="item1", score=1.0, metadata={})]

        def query_by_datapoint_id(self, anchor_id, tenant_id, env, space, top_k=10):
            return [ExplorerVectorHit(id="item1", score=1.0, metadata={})]

        def upsert(self, item_id, vector, tenant_id, env, space, metadata=None):  # pragma: no cover - unused
            return None

    repo = InMemoryVectorCorpusRepository(
        [
            VectorExplorerItem(
                id="item1",
                label="Item 1",
                tags=["tag1"],
                metrics={"size_hint": 1.0},
                source_ref={"uri": "s1"},
            )
        ]
    )

    fake_service = VectorExplorerService(
        repository=repo, vector_store=FakeVectorStore(), embedder=FakeEmbedder(), event_logger=lambda e: None
    )
    monkeypatch.setattr(routes, "_service", fake_service)

    client = TestClient(create_app())
    resp = client.get(
        "/vector-explorer/scene",
        params={"tenant_id": "t_demo", "env": "dev", "space": "demo", "query_mode": "all"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["nodes"][0]["id"] == "item1"
