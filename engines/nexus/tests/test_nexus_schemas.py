from engines.nexus.schemas import NexusDocument, NexusIngestRequest, NexusKind, NexusQueryRequest, NexusQueryResult


def test_nexus_ingest_space_naming() -> None:
    req = NexusIngestRequest(
        tenantId="t_demo",
        env="dev",
        kind=NexusKind.data,
        docs=[NexusDocument(id="1", text="hello")],
    )
    assert req.space == "nexus-t_demo-data-dev"


def test_nexus_query_result_default_hits() -> None:
    res = NexusQueryResult()
    assert res.hits == []


def test_nexus_query_request_defaults() -> None:
    req = NexusQueryRequest(tenantId="t_demo", env="dev", kind=NexusKind.style, query="q")
    assert req.top_k == 5


def test_nexus_document_optional_metadata() -> None:
    doc = NexusDocument(
        id="doc-1",
        text="hello",
        tenant_id="t_demo",
        env="dev",
        kind=NexusKind.data,
        tags=["a", "b"],
        metadata={"source": "unit-test"},
        refs={"episode_id": "ep-1"},
    )
    assert doc.tags == ["a", "b"]
    assert doc.metadata["source"] == "unit-test"
