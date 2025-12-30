"""Knowledge ingest/retrieval service."""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from engines.common.identity import RequestContext
from engines.storage.gcs_client import GcsClient

from engines.knowledge.models import KnowledgeDocument, KnowledgeScope
from engines.knowledge.repository import KnowledgeRepository, knowledge_repo_from_env
from engines.knowledge.schemas import KnowledgeIngestRequest, KnowledgeQueryRequest


class KnowledgeService:
    """Simple store that writes raw docs to RAW_BUCKET and indexes metadata."""

    def __init__(
        self,
        repository: KnowledgeRepository | None = None,
        storage: GcsClient | None = None,
    ) -> None:
        self._repo = repository or knowledge_repo_from_env()
        self._storage = storage or GcsClient()
        self.backend_name = getattr(self._repo, "backend_name", "bm25-filesystem")

    def ingest(self, ctx: RequestContext, request: KnowledgeIngestRequest) -> Dict[str, Any]:
        scope = self._build_scope(ctx)
        doc_id = request.doc_id or uuid.uuid4().hex
        env = ctx.env or "dev"
        key = f"knowledge/{scope.project_id}/{doc_id}.txt"
        raw_path = self._storage.upload_raw_media(scope.tenant_id, key, request.text, env=env)
        document = KnowledgeDocument(
            doc_id=doc_id,
            scope=scope,
            title=request.title or doc_id,
            text=request.text,
            metadata=request.metadata.copy(),
            raw_path=raw_path,
            created_at=datetime.now(timezone.utc),
        )
        self._repo.save_document(document)
        return {"doc_id": doc_id, "raw_path": raw_path}

    def query(
        self, ctx: RequestContext, request: KnowledgeQueryRequest
    ) -> List[Dict[str, Any]]:
        scope = self._build_scope(ctx)
        documents = self._repo.list_documents(scope)
        query_tokens = self._tokenize(request.query_text)
        scored: list[tuple[int, KnowledgeDocument]] = []
        for document in documents:
            score = self._score_document(document, query_tokens)
            scored.append((score, document))
        scored.sort(key=lambda item: (-item[0], -item[1].created_at.timestamp()))
        results: list[Dict[str, Any]] = []
        for score, document in scored[: request.limit]:
            results.append(
                {
                    "doc_id": document.doc_id,
                    "title": document.title,
                    "raw_path": document.raw_path,
                    "metadata": document.metadata,
                    "score": score,
                }
            )
        return results

    def _build_scope(self, ctx: RequestContext) -> KnowledgeScope:
        return KnowledgeScope(
            tenant_id=ctx.tenant_id,
            mode=ctx.mode or ctx.env or "dev",
            project_id=ctx.project_id,
            user_id=ctx.user_id,
            session_id=ctx.canvas_id,
        )

    def _tokenize(self, text: str) -> list[str]:
        return [token for token in re.split(r"\W+", text.lower()) if token]

    def _score_document(self, document: KnowledgeDocument, tokens: list[str]) -> int:
        if not tokens:
            return 0
        lower_text = document.text.lower()
        return sum(lower_text.count(token) for token in tokens)


def knowledge_service_factory(
    repository: KnowledgeRepository | None = None,
    storage: GcsClient | None = None,
) -> KnowledgeService:
    return KnowledgeService(repository=repository, storage=storage)
