"""Nexus RAG service: embed, vector search, hydrate documents."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable, List, Optional, Sequence

from engines.nexus.logging import ModelCallLog, ModelCallLogger, PromptSnapshot, UsageLogger
from engines.nexus.embedding import EmbeddingAdapter
from engines.nexus.schemas import NexusDocument, NexusEmbedding, NexusKind, NexusUsage
from engines.nexus.vector_store import NexusVectorStore, VectorHit


class NexusRagService:
    def __init__(
        self,
        embedder: EmbeddingAdapter,
        vector_store: NexusVectorStore,
        nexus_backend,
        usage_logger: Optional[UsageLogger] = None,
        model_call_logger: Optional[ModelCallLogger] = None,
    ) -> None:
        self._embedder = embedder
        self._vector_store = vector_store
        self._backend = nexus_backend
        self._usage_logger = usage_logger
        self._model_call_logger = model_call_logger

    def upsert_document(
        self,
        doc: NexusDocument,
        kind: NexusKind,
        tenant_id: str,
        env: str,
        tags: Optional[Sequence[str]] = None,
    ) -> NexusEmbedding:
        merged_tags = list(tags or [])
        merged_tags.extend(doc.tags)
        embedding_result = self._embedder.embed_text(doc.text)
        self._log_model_call(
            ModelCallLog(
                tenant_id=tenant_id,
                env=env,
                model_id=embedding_result.model_id,
                purpose="embed_upsert",
                prompt=PromptSnapshot(text=doc.text),
                output_dimensions=len(embedding_result.vector),
                episode_id=doc.refs.get("episode_id") if hasattr(doc, "refs") else None,
            )
        )
        emb = NexusEmbedding(
            doc_id=doc.id,
            tenant_id=tenant_id,
            env=env,
            kind=kind,
            embedding=embedding_result.vector,
            model_id=embedding_result.model_id,
            dimensions=len(embedding_result.vector),
            metadata=doc.metadata,
        )
        self._backend.write_snippet(
            kind,
            NexusDocument(
                id=doc.id,
                text=doc.text,
                tenant_id=tenant_id,
                env=env,
                kind=kind,
                tags=list(merged_tags),
                metadata=doc.metadata,
                refs=doc.refs,
            ),
            tags=list(merged_tags),
        )
        # TODO: async queue for vector upsert; currently inline
        self._vector_store.upsert(emb)
        return emb

    def query(
        self,
        tenant_id: str,
        env: str,
        kind: NexusKind,
        query_text: str,
        top_k: int = 5,
    ) -> List[NexusDocument]:
        embed = self._embedder.embed_text(query_text)
        self._log_model_call(
            ModelCallLog(
                tenant_id=tenant_id,
                env=env,
                model_id=embed.model_id,
                purpose="embed_query",
                prompt=PromptSnapshot(text=query_text),
                output_dimensions=len(embed.vector),
            )
        )
        hits = self._vector_store.query(
            vector=embed.vector, tenant_id=tenant_id, env=env, kind=kind, top_k=top_k
        )
        doc_ids = [h.doc_id for h in hits]
        docs = self._backend.get_snippets_by_ids(doc_ids)
        self._log_usage(
            NexusUsage(
                tenant_id=tenant_id,
                env=env,
                doc_ids=doc_ids,
                purpose="rag_query",
                scores=[h.score for h in hits],
                created_at=datetime.now(timezone.utc),
            )
        )
        return docs

    def _log_usage(self, usage: NexusUsage) -> None:
        if self._usage_logger:
            self._usage_logger(usage)

    def _log_model_call(self, call: ModelCallLog) -> None:
        if self._model_call_logger:
            self._model_call_logger(call)
