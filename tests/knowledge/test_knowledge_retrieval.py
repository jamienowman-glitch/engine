from __future__ import annotations

from engines.common.identity import RequestContext
from engines.knowledge.repository import FileKnowledgeRepository
from engines.knowledge.schemas import KnowledgeIngestRequest, KnowledgeQueryRequest
from engines.knowledge.service import KnowledgeService


def _build_context() -> RequestContext:
    return RequestContext(
        tenant_id="t_demo",
        mode="lab",
        project_id="p_demo",
        request_id="ctx-1",
        user_id="user123",
        env="dev",
    )


def test_knowledge_ingest_and_query_persistence(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("RAW_BUCKET", "test-knowledge-bucket")
    monkeypatch.setenv("KNOWLEDGE_BACKEND", "filesystem")
    knowledge_dir = tmp_path / "knowledge"
    monkeypatch.setenv("KNOWLEDGE_DIR", str(knowledge_dir))

    repo = FileKnowledgeRepository(base_dir=str(knowledge_dir))
    service = KnowledgeService(repository=repo)
    ctx = _build_context()

    service.ingest(
        ctx,
        KnowledgeIngestRequest(text="alpha document sample", title="alpha doc"),
    )
    service.ingest(
        ctx,
        KnowledgeIngestRequest(text="beta content example", title="beta doc"),
    )

    results = service.query(ctx, KnowledgeQueryRequest(query_text="alpha", limit=1))
    assert len(results) == 1
    assert results[0]["title"] == "alpha doc"

    service_restart = KnowledgeService(repository=FileKnowledgeRepository(base_dir=str(knowledge_dir)))
    results_after_restart = service_restart.query(ctx, KnowledgeQueryRequest(query_text="beta", limit=1))
    assert len(results_after_restart) == 1
    assert results_after_restart[0]["title"] == "beta doc"
