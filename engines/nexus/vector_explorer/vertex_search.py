"""Vertex Matching Engine backend for Vector Explorer (optional)."""
from __future__ import annotations

from typing import Any, Iterable, Sequence

try:  # pragma: no cover - optional dependency
    from google.cloud import aiplatform  # type: ignore
except Exception:  # pragma: no cover
    aiplatform = None

from engines.config import runtime_config
from engines.cost.vertex_guard import ensure_billable_vertex_allowed
from engines.nexus.embedding import EmbeddingAdapter, VertexEmbeddingAdapter
from engines.nexus.vector_explorer.schemas import VectorExplorerQuery
from engines.nexus.vector_explorer.search_backend import VectorSearchBackend


class VertexVectorSearchBackend(VectorSearchBackend):
    """Uses Vertex Matching Engine for similarity search."""

    def __init__(
        self,
        embedder: EmbeddingAdapter | None = None,
        endpoint: Any = None,
        project: str | None = None,
        location: str | None = None,
        index_endpoint_id: str | None = None,
        deployed_index_id: str | None = None,
        timeout_seconds: float = 10.0,
    ) -> None:
        ensure_billable_vertex_allowed("Vertex Explorer vector search")
        self._embedder = embedder or VertexEmbeddingAdapter()
        self._project = project or runtime_config.get_firestore_project()
        self._location = location or runtime_config.get_region() or "us-central1"
        self._endpoint_id = index_endpoint_id or runtime_config.get_vector_endpoint_id()
        self._deployed_index_id = deployed_index_id or runtime_config.get_vector_index_id()
        self._timeout = timeout_seconds
        self._endpoint = endpoint or self._init_endpoint()

    def _init_endpoint(self):
        if aiplatform is None:
            raise RuntimeError("google-cloud-aiplatform not installed for Vertex vector search")
        if not self._project or not self._endpoint_id:
            raise RuntimeError("VECTOR_ENDPOINT_ID and project are required for Vertex vector search")
        aiplatform.init(project=self._project, location=self._location)
        endpoint_path = f"projects/{self._project}/locations/{self._location}/indexEndpoints/{self._endpoint_id}"
        return aiplatform.MatchingEngineIndexEndpoint(index_endpoint_name=endpoint_path)  # type: ignore[attr-defined]

    def query_by_id(self, anchor_id: str, query: VectorExplorerQuery) -> Iterable[tuple[str, float]]:
        # Vertex Matching Engine requires a vector; without an embedding we cannot perform id-based search here.
        raise RuntimeError("query_by_id is not supported for VertexVectorSearchBackend without embeddings")

    def query_by_text(self, text: str, query: VectorExplorerQuery) -> Iterable[tuple[str, float]]:
        embed = self._embedder.embed_text(text)
        filters = {
            "namespace": "metadata",
            "allow": [
                {"tenant_id": query.tenant_id},
                {"env": query.env},
                {"kind": query.space},
            ],
        }
        response = self._endpoint.find_neighbors(  # type: ignore[attr-defined]
            deployed_index_id=self._deployed_index_id or "",
            queries=[{"embedding": list(embed.vector), "filter": filters}],
            neighbor_count=query.limit,
            timeout=self._timeout,
        )
        return _parse_neighbors(response)


def _parse_neighbors(response: Any) -> list[tuple[str, float]]:
    hits: list[tuple[str, float]] = []
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
        else:
            doc_id = neighbor.get("datapoint_id") or neighbor.get("id") or ""
            score = neighbor.get("distance") or neighbor.get("score") or 0.0
        hits.append((str(doc_id), float(score)))
    return hits
