from __future__ import annotations

import pytest

from engines.nexus.schemas import NexusEmbedding, NexusKind
from engines.nexus.vector_store import VectorStoreError, VertexVectorStore


class DummyEndpoint:
    def __init__(self):
        self.upserts = []
        self.queries = []
        self.removes = []
        self.deployed_indexes = ["idx"]

    def upsert_datapoints(self, datapoints, namespace=None, timeout=None):
        self.upserts.append({"datapoints": datapoints, "namespace": namespace, "timeout": timeout})

    def find_neighbors(self, deployed_index_id, queries, neighbor_count, timeout=None):
        self.queries.append(
            {
                "deployed_index_id": deployed_index_id,
                "queries": queries,
                "neighbor_count": neighbor_count,
                "timeout": timeout,
            }
        )
        return {
            "neighbors": [
                {"datapoint_id": "doc-1", "distance": 0.1, "attributes": {"tenant_id": "t_demo"}}
            ]
        }

    def remove_datapoints(self, datapoint_ids, namespace=None, timeout=None):
        self.removes.append({"ids": datapoint_ids, "namespace": namespace, "timeout": timeout})


class FailingEndpoint(DummyEndpoint):
    def find_neighbors(self, *args, **kwargs):
        raise TimeoutError("timeout")


def _embedding(kind: NexusKind = NexusKind.data) -> NexusEmbedding:
    return NexusEmbedding(
        doc_id="doc-1",
        tenant_id="t_demo",
        env="dev",
        kind=kind,
        embedding=[0.1, 0.2],
        model_id="text-embed",
    )


def test_upsert_sends_restricts_and_namespace():
    endpoint = DummyEndpoint()
    store = VertexVectorStore(index_id="idx", endpoint_id="ep1", endpoint=endpoint, project="p1")
    store.upsert(_embedding(NexusKind.style))

    assert endpoint.upserts, "expected upsert to be called"
    call = endpoint.upserts[0]
    datapoint = call["datapoints"][0]
    assert datapoint["datapoint_id"] == "doc-1"
    assert datapoint["restricts"][0]["allow"] == ["t_demo"]
    assert call["namespace"] == "style"


def test_query_parses_neighbors():
    endpoint = DummyEndpoint()
    store = VertexVectorStore(index_id="idx", endpoint_id="ep1", endpoint=endpoint, project="p1")
    hits = store.query([0.5, 0.6], tenant_id="t_demo", env="dev", kind=NexusKind.data, top_k=3)
    assert len(hits) == 1
    assert hits[0].doc_id == "doc-1"
    assert hits[0].score == pytest.approx(0.1)


def test_delete_uses_namespace():
    endpoint = DummyEndpoint()
    store = VertexVectorStore(index_id="idx", endpoint_id="ep1", endpoint=endpoint, project="p1")
    store.delete("doc-1", kind=NexusKind.chat)
    assert endpoint.removes[0]["namespace"] == "chat"


def test_query_raises_on_error():
    endpoint = FailingEndpoint()
    store = VertexVectorStore(index_id="idx", endpoint_id="ep1", endpoint=endpoint, project="p1")
    with pytest.raises(VectorStoreError):
        store.query([0.1], tenant_id="t_demo", env="dev", kind=NexusKind.data)


def test_query_requires_index_id():
    endpoint = DummyEndpoint()
    store = VertexVectorStore(index_id=None, endpoint_id="ep1", endpoint=endpoint, project="p1")
    with pytest.raises(VectorStoreError):
        store.query([0.1], tenant_id="t_demo", env="dev", kind=NexusKind.data)
