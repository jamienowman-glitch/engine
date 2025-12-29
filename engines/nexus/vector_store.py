"""Nexus vector store interfaces and Vertex AI implementation."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence

from engines.common.identity import RequestContext
from engines.common.selecta import SelectaResolver, get_selecta_resolver
from engines.config import runtime_config
from engines.cost.vertex_guard import ensure_billable_vertex_allowed
from engines.nexus.schemas import NexusEmbedding, NexusKind

try:  # pragma: no cover - optional dependency
    from google.cloud import aiplatform  # type: ignore
except Exception:  # pragma: no cover
    aiplatform = None

logger = logging.getLogger(__name__)


class VectorStoreError(RuntimeError):
    """Raised when the vector store cannot complete an operation."""


@dataclass
class VectorHit:
    doc_id: str
    score: float
    metadata: Dict[str, Any]


class NexusVectorStore:
    """Interface for vector search backends."""

    def upsert(self, embedding: NexusEmbedding) -> None:
        raise NotImplementedError

    def bulk_upsert(self, embeddings: Sequence[NexusEmbedding]) -> None:
        raise NotImplementedError

    def query(
        self,
        vector: Sequence[float],
        tenant_id: str,
        env: str,
        kind: NexusKind,
        top_k: int = 5,
    ) -> List[VectorHit]:
        raise NotImplementedError

    def delete(self, doc_id: str, kind: Optional[NexusKind] = None) -> None:
        raise NotImplementedError

    def health_check(self) -> bool:
        raise NotImplementedError


class VertexVectorStore(NexusVectorStore):
    """Vertex AI Vector Search backend."""

    def __init__(
        self,
        index_id: Optional[str] = None,
        endpoint_id: Optional[str] = None,
        project: Optional[str] = None,
        location: Optional[str] = None,
        timeout_seconds: float = 10.0,
        endpoint: Optional[Any] = None,
        selecta: Optional[SelectaResolver] = None,
    ) -> None:
        self._timeout = timeout_seconds
        self._endpoint = endpoint
        self._selecta = selecta or get_selecta_resolver()
        self.index_id = index_id
        self.endpoint_id = endpoint_id
        self.project = project
        self.location = location

    def upsert(self, embedding: NexusEmbedding) -> None:
        self._ensure_endpoint(embedding.tenant_id, embedding.env)
        datapoint = {
            "datapoint_id": embedding.doc_id,
            "feature_vector": embedding.embedding,
            "restricts": [
                {"namespace": "tenant_id", "allow": [embedding.tenant_id]},
                {"namespace": "env", "allow": [embedding.env]},
                {"namespace": "kind", "allow": [embedding.kind.value]},
            ],
            "attributes": embedding.metadata,
        }
        namespace = embedding.kind.value
        try:
            self._endpoint.upsert_datapoints(
                datapoints=[datapoint],
                namespace=namespace,
                timeout=self._timeout,
            )
        except Exception as exc:
            raise VectorStoreError(f"Vertex upsert failed: {exc}") from exc

    def bulk_upsert(self, embeddings: Sequence[NexusEmbedding]) -> None:
        if not embeddings:
            return
        self._ensure_endpoint(embeddings[0].tenant_id, embeddings[0].env)
        datapoints = []
        for emb in embeddings:
            datapoints.append(
                {
                    "datapoint_id": emb.doc_id,
                    "feature_vector": emb.embedding,
                    "restricts": [
                        {"namespace": "tenant_id", "allow": [emb.tenant_id]},
                        {"namespace": "env", "allow": [emb.env]},
                        {"namespace": "kind", "allow": [emb.kind.value]},
                    ],
                    "attributes": emb.metadata,
                }
            )
        namespace = embeddings[0].kind.value
        try:
            self._endpoint.upsert_datapoints(
                datapoints=datapoints, namespace=namespace, timeout=self._timeout
            )
        except Exception as exc:
            raise VectorStoreError(f"Vertex bulk upsert failed: {exc}") from exc

    def query(
        self,
        vector: Sequence[float],
        tenant_id: str,
        env: str,
        kind: NexusKind,
        top_k: int = 5,
    ) -> List[VectorHit]:
        self._ensure_endpoint(tenant_id, env)
        if not self.index_id:
            raise VectorStoreError("Vertex index_id is required for queries")
        filters = {
            "namespace": "metadata",
            "allow": [
                {"tenant_id": tenant_id},
                {"env": env},
                {"kind": kind.value},
            ],
        }
        try:
            response = self._endpoint.find_neighbors(  # type: ignore[attr-defined]
                deployed_index_id=self.index_id or "",
                queries=[{"embedding": list(vector), "filter": filters}],
                neighbor_count=top_k,
                timeout=self._timeout,
            )
        except Exception as exc:
            raise VectorStoreError(f"Vertex query failed: {exc}") from exc
        return self._parse_neighbors(response)

    def delete(self, doc_id: str, kind: Optional[NexusKind] = None) -> None:
        namespace = kind.value if kind else None
        try:
            self._endpoint.remove_datapoints(  # type: ignore[attr-defined]
                datapoint_ids=[doc_id], namespace=namespace, timeout=self._timeout
            )
        except Exception as exc:
            raise VectorStoreError(f"Vertex delete failed: {exc}") from exc

    def health_check(self) -> bool:
        try:
            deployed = getattr(self._endpoint, "deployed_indexes", None)
            if deployed is None:
                return True
            return bool(deployed)
        except Exception as exc:
            logger.warning("Vertex vector health check failed: %s", exc)
            raise VectorStoreError(f"Vertex health check failed: {exc}") from exc

    def _parse_neighbors(self, response: Any) -> List[VectorHit]:
        hits: List[VectorHit] = []
        neighbors = []
        if isinstance(response, dict):
            neighbors = response.get("neighbors", [])
        elif hasattr(response, "neighbors"):
            neighbors = response.neighbors  # type: ignore[attr-defined]
        for neighbor in neighbors:
            if hasattr(neighbor, "datapoint"):
                dp = neighbor.datapoint
                doc_id = getattr(dp, "datapoint_id", None) or getattr(dp, "id", "")
                score = getattr(neighbor, "distance", None) or getattr(neighbor, "score", 0.0)
                metadata = getattr(dp, "restricts", None) or getattr(dp, "attributes", {}) or {}
            else:
                doc_id = neighbor.get("datapoint_id") or neighbor.get("id") or ""
                score = neighbor.get("distance") or neighbor.get("score") or 0.0
                metadata = neighbor.get("restricts") or neighbor.get("attributes") or {}
            hits.append(VectorHit(doc_id=doc_id, score=float(score), metadata=dict(metadata)))
        return hits

    # --- internal ---
    def _ensure_endpoint(self, tenant_id: str, env: str) -> None:
        ensure_billable_vertex_allowed("Vertex Vector Search")
        if getattr(self, "_endpoint", None) is not None:
            return
        cfg = RequestContext(request_id="selecta", tenant_id=tenant_id, env=env)
        vs_cfg = self._selecta.vector_store_config(cfg)
        self.index_id = vs_cfg.index_id
        self.endpoint_id = vs_cfg.endpoint_id
        self.project = vs_cfg.project
        self.location = vs_cfg.region or runtime_config.get_env_region_fallback()
        if aiplatform is None:
            raise VectorStoreError("google-cloud-aiplatform not installed for Vertex Vector Search")
        if not self.project or not self.endpoint_id:
            raise VectorStoreError("Vertex vector project/endpoint are required")
        aiplatform.init(project=self.project, location=self.location)
        endpoint_path = f"projects/{self.project}/locations/{self.location}/indexEndpoints/{self.endpoint_id}"
        self._endpoint = aiplatform.MatchingEngineIndexEndpoint(index_endpoint_name=endpoint_path)  # type: ignore[attr-defined]
