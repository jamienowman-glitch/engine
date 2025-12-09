from __future__ import annotations

from typing import List

import pytest

from engines.nexus.embedding import EmbeddingAdapter, EmbeddingResult
from engines.nexus.rag_service import NexusRagService
from engines.nexus.schemas import NexusDocument, NexusKind, NexusUsage
from engines.nexus.vector_store import NexusVectorStore, VectorHit, VectorStoreError
from engines.nexus.logging import ModelCallLog


class DummyBackend:
    def __init__(self):
        self.snippets = {}

    def write_snippet(self, kind, doc, tags=None):
        self.snippets[doc.id] = doc

    def get_snippets_by_ids(self, ids: List[str]):
        return [self.snippets[i] for i in ids if i in self.snippets]


class DummyEmbedder(EmbeddingAdapter):
    def __init__(self):
        self.calls = []

    def embed_text(self, text: str, model_id=None) -> EmbeddingResult:
        self.calls.append(text)
        return EmbeddingResult(vector=[1.0, 2.0], model_id=model_id or "text-embed")

    def embed_image(self, image_uri: str, model_id=None) -> EmbeddingResult:
        raise NotImplementedError


class DummyVectorStore(NexusVectorStore):
    def __init__(self):
        self.upserts = []
        self.queries = []
        self.fail_query = False

    def upsert(self, embedding):
        self.upserts.append(embedding)

    def bulk_upsert(self, embeddings):
        for emb in embeddings:
            self.upserts.append(emb)

    def query(self, vector, tenant_id, env, kind, top_k=5):
        if self.fail_query:
            raise VectorStoreError("query failed")
        self.queries.append({"vector": vector, "tenant_id": tenant_id, "env": env, "kind": kind, "top_k": top_k})
        return [VectorHit(doc_id="doc-1", score=0.1, metadata={})]

    def delete(self, doc_id: str, kind=None):
        return None

    def health_check(self):
        return True


def test_upsert_document_writes_backend_and_vector():
    embedder = DummyEmbedder()
    store = DummyVectorStore()
    backend = DummyBackend()
    service = NexusRagService(embedder=embedder, vector_store=store, nexus_backend=backend)

    doc = NexusDocument(id="doc-1", text="hello", metadata={"source": "unit"})
    emb = service.upsert_document(doc, kind=NexusKind.data, tenant_id="t_demo", env="dev", tags=["a"])

    assert backend.snippets["doc-1"].tags == ["a"]
    assert store.upserts[0].doc_id == "doc-1"
    assert emb.dimensions == 2


def test_query_returns_hydrated_docs_and_logs_usage():
    embedder = DummyEmbedder()
    store = DummyVectorStore()
    backend = DummyBackend()
    backend.write_snippet(NexusKind.data, NexusDocument(id="doc-1", text="hi"), tags=["a"])
    logged_usage = []
    logged_calls = []

    def log_usage(u: NexusUsage):
        logged_usage.append(u)

    def log_call(c: ModelCallLog):
        logged_calls.append(c)

    service = NexusRagService(
        embedder=embedder,
        vector_store=store,
        nexus_backend=backend,
        usage_logger=log_usage,
        model_call_logger=log_call,
    )
    docs = service.query(tenant_id="t_demo", env="dev", kind=NexusKind.data, query_text="query", top_k=3)
    assert docs[0].id == "doc-1"
    assert logged_usage and logged_usage[0].doc_ids == ["doc-1"]
    assert logged_calls and logged_calls[0].purpose == "embed_query"


def test_query_raises_on_vector_error():
    embedder = DummyEmbedder()
    store = DummyVectorStore()
    store.fail_query = True
    backend = DummyBackend()
    service = NexusRagService(embedder=embedder, vector_store=store, nexus_backend=backend)
    with pytest.raises(VectorStoreError):
        service.query(tenant_id="t_demo", env="dev", kind=NexusKind.data, query_text="boom")
