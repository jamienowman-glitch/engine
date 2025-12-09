"""Ingestion service for Haze vector explorer (production path)."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Optional, Sequence

from engines.config import runtime_config
from engines.dataset.events.schemas import DatasetEvent
from engines.logging.events.engine import run as log_dataset_event
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
    ) -> None:
        self._corpus = corpus_repo or FirestoreVectorCorpusRepository()
        self._vector_store = vector_store or VertexExplorerVectorStore()
        self._embedder = embedder or VertexEmbeddingAdapter()
        self._gcs = gcs_client or GcsClient()
        self._event_logger = event_logger or log_dataset_event
        cfg = runtime_config.config_snapshot()
        self._tenant_default = cfg.get("tenant_id")
        self._env_default = cfg.get("env") or "dev"

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
        source_ref: Optional[Dict[str, str]] = None,
    ) -> IngestResult:
        tenant = tenant_id or self._tenant_default
        if not tenant:
            raise IngestError("tenant_id is required")
        if not env:
            raise IngestError("env is required")
        if content_type not in {"text", "image", "video", "pdf"}:
            raise IngestError("content_type must be one of text|image|video|pdf")

        asset_id = uuid.uuid4().hex
        gcs_uri = None
        source_ref = dict(source_ref or {})
        source_ref.update({"content_type": content_type})

        self._log_event(
            DatasetEvent(
                tenantId=tenant,
                env=env,
                surface="vector_ingest",
                agentId="vector_ingest",
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
        vector, model_id = self._embed_for_content(content_type, text_content, file_bytes)
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
                tenantId=tenant,
                env=env,
                surface="vector_ingest",
                agentId="vector_ingest",
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
        return IngestResult(item=item, gcs_uri=gcs_uri)

    def _embed_for_content(
        self,
        content_type: str,
        text_content: Optional[str],
        file_bytes: Optional[bytes],
    ) -> tuple[Sequence[float], str]:
        try:
            if content_type == "image":
                if file_bytes is None:
                    raise IngestError("image content requires file_bytes")
                result = self._embedder.embed_image_bytes(file_bytes)  # type: ignore[attr-defined]
                return result.vector, result.model_id
            # video/pdf/text → require text_content for embedding
            if not text_content:
                raise IngestError("text_content is required for text/video/pdf ingest")
            result = self._embedder.embed_text(text_content)
            return result.vector, result.model_id
        except IngestError:
            self._log_event(
                DatasetEvent(
                    tenantId=tenant_id or self._tenant_default or "t_unknown",
                    env=env,
                    surface="vector_ingest",
                    agentId="vector_ingest",
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
            return
        try:
            self._event_logger(event)
        except Exception:
            return
