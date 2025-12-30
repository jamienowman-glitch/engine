"""Vector Explorer service: query corpus/vector backend and return scenes."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, List, Optional

from engines.config import runtime_config
from engines.dataset.events.schemas import DatasetEvent
from engines.logging.events.engine import run as log_dataset_event
from engines.logging.events.contract import compliance_run_enabled
from engines.budget.service import get_budget_service, BudgetService
from engines.budget.models import UsageEvent
from engines.nexus.embedding import EmbeddingAdapter, VertexEmbeddingAdapter
from engines.common.identity import RequestContext
from engines.nexus.vector_explorer.repository import FirestoreVectorCorpusRepository, VectorCorpusRepository
from engines.nexus.vector_explorer.scene_builder import build_scene
from engines.nexus.vector_explorer.schemas import (
    QueryMode,
    VectorExplorerItem,
    VectorExplorerQuery,
    VectorExplorerResult,
)
from engines.nexus.vector_explorer.vector_store import ExplorerVectorStore, VertexExplorerVectorStore, VectorStoreConfigError
from engines.scene_engine.core.types import Scene


@dataclass
class VectorExplorerDeps:
    repository: VectorCorpusRepository
    vector_store: ExplorerVectorStore
    embedder: EmbeddingAdapter
    event_logger: Optional[callable] = None


class VectorExplorerService:
    def __init__(
        self,
        repository: Optional[VectorCorpusRepository] = None,
        vector_store: Optional[ExplorerVectorStore] = None,
        embedder: Optional[EmbeddingAdapter] = None,
        event_logger: Optional[callable] = None,
        budget_service: Optional[BudgetService] = None,
    ) -> None:
        self._repo = repository or FirestoreVectorCorpusRepository()
        self._vector_store = vector_store or VertexExplorerVectorStore()
        self._embedder = embedder or VertexEmbeddingAdapter()
        resolved_logger = event_logger or log_dataset_event
        if compliance_run_enabled() and event_logger is None:
            raise RuntimeError("vector explorer requires an explicit event logger under compliance runs")
        self._event_logger = resolved_logger
        self._budget_service = budget_service or get_budget_service()

    def _envelope_kwargs(
        self,
        query: VectorExplorerQuery,
        context: RequestContext | None,
        step_id: str,
        run_id: Optional[str] = None,
    ) -> dict[str, Any]:
        request_id = query.trace_id or uuid.uuid4().hex
        return {
            "tenantId": query.tenant_id,
            "env": query.env,
            "mode": context.mode if context else query.env,
            "project_id": context.project_id if context else runtime_config._default_project_id(),
            "app_id": context.app_id if context else None,
            "surface": "vector_explorer",
            "surface_id": context.surface_id if context and context.surface_id else query.space or "vector_explorer",
            "agentId": "vector_explorer",
            "run_id": run_id or request_id,
            "step_id": step_id,
            "traceId": request_id,
            "requestId": request_id,
        }

    def query_items(
        self, query: VectorExplorerQuery, context: RequestContext | None = None
    ) -> VectorExplorerResult:
        items: List[VectorExplorerItem]
        if query.query_mode == QueryMode.all:
            items = list(
                self._repo.list_filtered(
                    tenant_id=query.tenant_id,
                    env=query.env,
                    space=query.space,
                    tags=query.tags,
                    metadata_filters=query.metadata_filters,
                    limit=query.limit,
                )
            )
        elif query.query_mode == QueryMode.similar_to_id:
            if not query.anchor_id:
                raise ValueError("anchor_id is required for similar_to_id")
            items = self._hydrate_similar_by_id(query, query.anchor_id, context)
        elif query.query_mode == QueryMode.similar_to_text:
            if not query.query_text:
                raise ValueError("query_text is required for similar_to_text")
            items = self._hydrate_similar_by_text(query, query.query_text, context)
        else:  # pragma: no cover - Enum guards
            items = []

        self._log_event(
            DatasetEvent(
                **self._envelope_kwargs(
                    query,
                    context,
                    step_id=f"vector_explorer.{query.query_mode.value}",
                ),
                input={
                    "query_mode": query.query_mode.value,
                    "space": query.space,
                    "tags": query.tags,
                    "anchor_id": query.anchor_id,
                    "trace_id": query.trace_id,
                },
                output={"count": len(items)},
                metadata={"kind": "vector_explorer.query"},
            )
        )
        return VectorExplorerResult(items=items, tenant_id=query.tenant_id, env=query.env, trace_id=query.trace_id)

    def build_scene_from_query(
        self, query: VectorExplorerQuery, context: RequestContext | None = None
    ) -> Scene:
        result = self.query_items(query, context)
        scene = build_scene(result.items)
        self._log_event(
            DatasetEvent(
                **self._envelope_kwargs(
                    query,
                    context,
                    step_id="vector_explorer.scene_composed",
                ),
                input={"trace_id": query.trace_id, "item_ids": [i.id for i in result.items]},
                output={"scene_id": scene.sceneId, "node_count": len(scene.nodes)},
                metadata={"kind": "vector_explorer.scene_composed"},
            )
        )
        return scene

    def _hydrate_similar_by_text(
        self,
        query: VectorExplorerQuery,
        text: str,
        context: RequestContext | None,
    ) -> List[VectorExplorerItem]:
        try:
            ctx = context or RequestContext(request_id="vector_explorer", tenant_id=query.tenant_id, env=query.env)
            embed = self._embedder.embed_text(text, context=ctx)
            hits = self._vector_store.query(
                vector=embed.vector,
                tenant_id=query.tenant_id,
                env=query.env,
                space=query.space,
                top_k=query.limit,
            )
            est_tokens = max(1, len(text) // 4)
            self._budget_service.record_usage(
                ctx,
                [
                    UsageEvent(
                        tenant_id=query.tenant_id,
                        env=query.env,
                        surface="vector_explorer",
                        tool_type="embedding",
                        tool_id="vector_explorer",
                        provider="vertex",
                        model_or_plan_id=embed.model_id,
                        tokens_input=est_tokens,
                        tokens_output=0,
                        cost=0,
                        request_id=ctx.request_id,
                        trace_id=query.trace_id or ctx.request_id,
                        run_id=query.trace_id or ctx.request_id,
                        step_id=f"vector_explorer.{query.query_mode.value}",
                    )
                ],
            )
        except VectorStoreConfigError as exc:
            raise ValueError(str(exc))
        items: List[VectorExplorerItem] = []
        for hit in hits:
            item = self._repo.get(query.tenant_id, query.env, hit.id)
            if not item:
                continue
            item.similarity_score = hit.score
            items.append(item)
        return items

    def _hydrate_similar_by_id(
        self, query: VectorExplorerQuery, anchor_id: str, context: RequestContext | None
    ) -> List[VectorExplorerItem]:
        try:
            hits = self._vector_store.query_by_datapoint_id(
                anchor_id=anchor_id,
                tenant_id=query.tenant_id,
                env=query.env,
                space=query.space,
                top_k=query.limit,
            )
        except VectorStoreConfigError as exc:
            raise ValueError(str(exc))
        items: List[VectorExplorerItem] = []
        for hit in hits:
            item = self._repo.get(query.tenant_id, query.env, hit.id)
            if not item:
                continue
            item.similarity_score = hit.score
            items.append(item)
        return items

    def _log_event(self, event: DatasetEvent) -> None:
        if not self._event_logger:
            raise RuntimeError("vector explorer event logger is required")
        self._event_logger(event)


def _dataset_event_logger(event: DatasetEvent) -> None:
    log_dataset_event(event)
