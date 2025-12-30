"""Ingestion service for Haze vector explorer (production path)."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Sequence

from engines.config import runtime_config
from engines.common.identity import RequestContext
from engines.dataset.events.schemas import DatasetEvent
from engines.logging.audit import emit_audit_event
from engines.logging.events.contract import compliance_run_enabled
from engines.logging.events.engine import run as log_dataset_event
from engines.budget.service import get_budget_service, BudgetService
from engines.budget.models import UsageEvent
from engines.nexus.embedding import EmbeddingAdapter, VertexEmbeddingAdapter
from engines.nexus.vector_explorer.repository import FirestoreVectorCorpusRepository, VectorCorpusRepository
from engines.nexus.vector_explorer.schemas import VectorExplorerItem
from engines.nexus.vector_explorer.vector_store import ExplorerVectorStore, VertexExplorerVectorStore, VectorStoreConfigError
from engines.storage.gcs_client import GcsClient


class IngestError(RuntimeError):
    """Raised for ingest failures."""


@dataclass
class IngestResult:
    item: VectorExplorerItem
    gcs_uri: Optional[str]


class VectorIngestService:
    def __init__(
        self,
        corpus_repo: Optional[VectorCorpusRepository] = None,
        vector_store: Optional[ExplorerVectorStore] = None,
        embedder: Optional[EmbeddingAdapter] = None,
        gcs_client: Optional[GcsClient] = None,
        event_logger: Optional[callable] = None,
        budget_service: Optional[BudgetService] = None,
    ) -> None:
        self._corpus = corpus_repo or FirestoreVectorCorpusRepository()
        self._vector_store = vector_store or VertexExplorerVectorStore()
        self._embedder = embedder or VertexEmbeddingAdapter()
        self._gcs = gcs_client or GcsClient()
        self._event_logger = event_logger or log_dataset_event
        if compliance_run_enabled() and event_logger is None:
            self._event_logger = log_dataset_event
        self._budget_service = budget_service or get_budget_service()

    def _envelope_kwargs(
        self,
        tenant_id: str,
        env: str,
        context: RequestContext | None,
        surface: str,
        step_id: str,
        run_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> dict[str, Any]:
        resolved_request_id = (
            request_id
            or (context.request_id if context and context.request_id else None)
            or uuid.uuid4().hex
        )
        return {
            "tenantId": tenant_id,
            "env": env,
            "mode": context.mode if context else env,
            "project_id": context.project_id if context else runtime_config._default_project_id(),
            "app_id": context.app_id if context else None,
            "surface": surface,
            "surface_id": context.surface_id if context and context.surface_id else surface,
            "agentId": "vector_ingest",
            "run_id": run_id or resolved_request_id,
            "step_id": step_id,
            "traceId": resolved_request_id,
            "requestId": resolved_request_id,
        }

    def ingest(
        self,
        *,
        tenant_id: str,
        env: str,
        space: str,
        content_type: str,
        label: str,
        tags: Sequence[str],
        text_content: Optional[str],
        file_bytes: Optional[bytes],
        filename: Optional[str],
        user_id: Optional[str] = None,
        source_ref: Optional[Dict[str, str]] = None,
        context: RequestContext | None = None,
    ) -> IngestResult:
        tenant = tenant_id
        if not tenant or not env:
            raise IngestError("tenant_id and env are required")
        if content_type not in {"text", "image", "video", "pdf"}:
            raise IngestError("content_type must be one of text|image|video|pdf")

        request_id = context.request_id if context else uuid.uuid4().hex

        asset_id = uuid.uuid4().hex
        gcs_uri = None
        source_ref = dict(source_ref or {})
        source_ref.update({"content_type": content_type})

        self._log_event(
            DatasetEvent(
                **self._envelope_kwargs(
                    tenant,
                    env,
                    context,
                    surface=space,
                    step_id="vector_ingest.attempt",
                    request_id=request_id,
                ),
                input={
                    "content_type": content_type,
                    "space": space,
                    "tags": list(tags),
                    "label": label,
                },
                output={},
                metadata={"kind": "vector_ingest.attempt"},
            )
        )
        # 1) Persist to storage/Nexus-like path (GCS for binaries).
        if file_bytes is not None and filename:
            path = f"{asset_id}/{filename}"
            gcs_uri = self._gcs.upload_raw_media(tenant, path, file_bytes)
            source_ref["gcs_uri"] = gcs_uri

        # 2) Embed (real embedding) and upsert to vector index.
        vector, model_id, est_tokens = self._embed_for_content(
            content_type=content_type,
            text_content=text_content,
            file_bytes=file_bytes,
            tenant_id=tenant,
            env=env,
            context=context,
        )
        metadata = {
            "tenant_id": tenant,
            "env": env,
            "space": space,
            "content_type": content_type,
            "label": label,
            "tags": list(tags),
            "model_id": model_id,
        }
        try:
            self._vector_store.upsert(
                item_id=asset_id,
                vector=vector,
                tenant_id=tenant,
                env=env,
                space=space,
                metadata=metadata,
            )
        except Exception as exc:
            raise IngestError(f"vector upsert failed: {exc}")
        usage_context = context or RequestContext(
            request_id=request_id,
            tenant_id=tenant,
            env=env,
            project_id=context.project_id if context else runtime_config._default_project_id(),
            surface_id=context.surface_id if context else space,
            app_id=context.app_id if context else None,
            user_id=user_id,
        )
        self._record_usage(usage_context, model_id=model_id, tokens=est_tokens)

        # 3) Corpus record
        item = VectorExplorerItem(
            id=asset_id,
            label=label,
            tags=list(tags),
            metrics={},
            similarity_score=None,
            source_ref=source_ref,
            vector_ref=asset_id,
        )
        self._write_corpus(tenant, env, space, item)

        # 4) Log
        self._log_event(
            DatasetEvent(
                **self._envelope_kwargs(
                    tenant,
                    env,
                    context,
                    surface=space,
                    step_id="vector_ingest.success",
                    request_id=request_id,
                ),
                input={
                    "content_type": content_type,
                    "space": space,
                    "tags": list(tags),
                    "label": label,
                },
                output={"asset_id": asset_id, "gcs_uri": gcs_uri},
                metadata={"kind": "vector_ingest.success"},
            )
        )
        emit_audit_event(
            usage_context,
            action="vector_ingest:create",
            surface="vector_explorer",
            metadata={"asset_id": asset_id, "space": space},
        )
        return IngestResult(item=item, gcs_uri=gcs_uri)

    def _embed_for_content(
        self,
        content_type: str,
        text_content: Optional[str],
        file_bytes: Optional[bytes],
        tenant_id: Optional[str],
        env: Optional[str],
        context: RequestContext | None,
    ) -> tuple[Sequence[float], str, int]:
        ctx = context or RequestContext(request_id="vector_ingest", tenant_id=tenant_id or "", env=env or "")
        try:
            if content_type == "image":
                if file_bytes is None:
                    raise IngestError("image content requires file_bytes")
                result = self._embedder.embed_image_bytes(file_bytes, context=ctx)  # type: ignore[attr-defined]
                return result.vector, result.model_id, 0
            # video/pdf/text → require text_content for embedding
            if not text_content:
                raise IngestError("text_content is required for text/video/pdf ingest")
            result = self._embedder.embed_text(text_content, context=ctx)
            est_tokens = max(1, len(text_content) // 4)
            return result.vector, result.model_id, est_tokens
        except IngestError:
            self._log_event(
                DatasetEvent(
                    **self._envelope_kwargs(
                        tenant_id or "",
                        env or "",
                        ctx,
                        surface="vector_ingest",
                        step_id="vector_ingest.fail",
                        request_id=ctx.request_id,
                    ),
                    input={"content_type": content_type},
                    output={},
                    metadata={"kind": "vector_ingest.fail"},
                )
            )
            raise
        except Exception as exc:
            raise IngestError(f"embedding failed: {exc}") from exc

    def _write_corpus(self, tenant_id: str, env: str, space: str, item: VectorExplorerItem) -> None:
        payload = {
            "id": item.id,
            "tenant_id": tenant_id,
            "env": env,
            "space": space,
            "label": item.label,
            "tags": item.tags,
            "metrics": item.metrics,
            "vector_ref": item.vector_ref,
            "source_ref": item.source_ref,
            "created_at": datetime.now(timezone.utc),
        }
        self._corpus.write_record(tenant_id, payload)

    def _log_event(self, event: DatasetEvent) -> None:
        if not self._event_logger:
            raise RuntimeError("vector ingest event logger is required")
        self._event_logger(event)

    def _record_usage(self, context: RequestContext, model_id: str, tokens: int) -> None:
        try:
            self._budget_service.record_usage(
                context,
                [
                    UsageEvent(
                        tenant_id=context.tenant_id,
                        env=context.env,
                        surface="vector_explorer",
                        tool_type="embedding",
                        tool_id="vector_ingest",
                        provider="vertex",
                        model_or_plan_id=model_id,
                        tokens_input=tokens,
                        tokens_output=0,
                        cost=0,
                        request_id=context.request_id,
                        trace_id=context.request_id,
                        run_id=context.request_id,
                        step_id="vector_ingest.embedding",
                    )
                ],
            )
        except Exception:
            return


def _noop_event_logger(event: DatasetEvent) -> None:
    log_dataset_event(event)
