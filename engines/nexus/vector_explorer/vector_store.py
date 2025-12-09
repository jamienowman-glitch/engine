"""Vector store adapter for Vector Explorer using Vertex Matching Engine."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

try:  # pragma: no cover - optional dependency
    from google.cloud import aiplatform  # type: ignore
except Exception:  # pragma: no cover
    aiplatform = None

from engines.config import runtime_config


class VectorStoreConfigError(RuntimeError):
    """Raised when vector backend configuration is missing or invalid."""


@dataclass
class ExplorerVectorHit:
    id: str
    score: float
    metadata: Dict[str, Any]


class ExplorerVectorStore:
    def upsert(
        self,
        item_id: str,
        vector: Sequence[float],
        tenant_id: str,
        env: str,
        space: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        raise NotImplementedError

    def query(
        self,
        vector: Sequence[float],
        tenant_id: str,
        env: str,
        space: str,
        top_k: int = 10,
    ) -> List[ExplorerVectorHit]:
        raise NotImplementedError

    def query_by_datapoint_id(
        self,
        anchor_id: str,
        tenant_id: str,
        env: str,
        space: str,
        top_k: int = 10,
    ) -> List[ExplorerVectorHit]:
        raise NotImplementedError


class VertexExplorerVectorStore(ExplorerVectorStore):
    """Vertex Matching Engine implementation."""

    def __init__(
        self,
        endpoint: Any = None,
        project: Optional[str] = None,
        location: Optional[str] = None,
        deployed_index_id: Optional[str] = None,
        index_endpoint_id: Optional[str] = None,
        timeout_seconds: float = 10.0,
    ) -> None:
        self.project = project or runtime_config.get_vector_project() or runtime_config.get_firestore_project()
        self.location = location or runtime_config.get_region() or "us-central1"
        self.deployed_index_id = deployed_index_id or runtime_config.get_vector_index_id()
        self.index_endpoint_id = index_endpoint_id or runtime_config.get_vector_endpoint_id()
        self._timeout = timeout_seconds
        self._endpoint = endpoint or self._init_endpoint()

    def _init_endpoint(self):
        if aiplatform is None:
            raise VectorStoreConfigError("google-cloud-aiplatform not installed for Vertex vector search")
        if not self.project or not self.index_endpoint_id or not self.deployed_index_id:
            raise VectorStoreConfigError("VECTOR_PROJECT_ID/GCP_PROJECT_ID, VECTOR_ENDPOINT_ID, VECTOR_INDEX_ID are required")
        aiplatform.init(project=self.project, location=self.location)
        endpoint_path = f"projects/{self.project}/locations/{self.location}/indexEndpoints/{self.index_endpoint_id}"
        return aiplatform.MatchingEngineIndexEndpoint(index_endpoint_name=endpoint_path)  # type: ignore[attr-defined]

    def upsert(
        self,
        item_id: str,
        vector: Sequence[float],
        tenant_id: str,
        env: str,
        space: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        datapoint = {
            "datapoint_id": item_id,
            "feature_vector": list(vector),
            "restricts": [
                {"namespace": "tenant_id", "allow": [tenant_id]},
                {"namespace": "env", "allow": [env]},
                {"namespace": "space", "allow": [space]},
            ],
            "attributes": metadata or {},
        }
        try:
            self._endpoint.upsert_datapoints(  # type: ignore[attr-defined]
                datapoints=[datapoint], namespace=space, timeout=self._timeout
            )
        except Exception as exc:
            raise VectorStoreConfigError(f"Vertex upsert failed: {exc}") from exc

    def query(
        self,
        vector: Sequence[float],
        tenant_id: str,
        env: str,
        space: str,
        top_k: int = 10,
    ) -> List[ExplorerVectorHit]:
        filters = {
            "namespace": "metadata",
            "allow": [
                {"tenant_id": tenant_id},
                {"env": env},
                {"space": space},
            ],
        }
        try:
            response = self._endpoint.find_neighbors(  # type: ignore[attr-defined]
                deployed_index_id=self.deployed_index_id or "",
                queries=[{"embedding": list(vector), "filter": filters}],
                neighbor_count=top_k,
                timeout=self._timeout,
            )
        except Exception as exc:
            raise VectorStoreConfigError(f"Vertex query failed: {exc}") from exc
        return self._parse_neighbors(response)

    def _parse_neighbors(self, response: Any) -> List[ExplorerVectorHit]:
        hits: List[ExplorerVectorHit] = []
        neighbors: Iterable[Any] = []
        if isinstance(response, dict):
            neighbors = response.get("neighbors", [])
        elif hasattr(response, "neighbors"):
            neighbors = response.neighbors  # type: ignore[attr-defined]
        for neighbor in neighbors:
            if hasattr(neighbor, "datapoint"):
                dp = neighbor.datapoint
                doc_id = getattr(dp, "datapoint_id", None) or getattr(dp, "id", "")
                score = getattr(neighbor, "distance", None) or getattr(neighbor, "score", 0.0)
                metadata = getattr(dp, "attributes", None) or {}
            else:
                doc_id = neighbor.get("datapoint_id") or neighbor.get("id") or ""
                score = neighbor.get("distance") or neighbor.get("score") or 0.0
                metadata = neighbor.get("attributes") or {}
            hits.append(ExplorerVectorHit(id=str(doc_id), score=float(score), metadata=dict(metadata)))
        return hits

    def query_by_datapoint_id(
        self,
        anchor_id: str,
        tenant_id: str,
        env: str,
        space: str,
        top_k: int = 10,
    ) -> List[ExplorerVectorHit]:
        filters = {
            "namespace": "metadata",
            "allow": [
                {"tenant_id": tenant_id},
                {"env": env},
                {"space": space},
            ],
        }
        try:
            response = self._endpoint.find_neighbors(  # type: ignore[attr-defined]
                deployed_index_id=self.deployed_index_id or "",
                queries=[{"datapoint_id": anchor_id, "filter": filters}],
                neighbor_count=top_k,
                timeout=self._timeout,
            )
        except Exception as exc:
            raise VectorStoreConfigError(f"Vertex query_by_datapoint_id failed: {exc}") from exc
        return self._parse_neighbors(response)
