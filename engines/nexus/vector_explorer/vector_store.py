"""Vector store adapter for Vector Explorer using Vertex Matching Engine."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

try:  # pragma: no cover - optional dependency
    from google.cloud import aiplatform  # type: ignore
    from google.cloud.aiplatform.matching_engine.matching_engine_index_endpoint import Namespace  # type: ignore
except Exception:  # pragma: no cover
    aiplatform = None
    Namespace = None

from engines.common.identity import RequestContext
from engines.common.selecta import SelectaResolver, get_selecta_resolver
from engines.config import runtime_config
from engines.cost.vertex_guard import ensure_billable_vertex_allowed


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
        timeout_seconds: float = 10.0,
        selecta: Optional[SelectaResolver] = None,
    ) -> None:
        self._timeout = timeout_seconds
        self._index = None
        self._endpoint = endpoint
        self._selecta = selecta or get_selecta_resolver()
        self.project = None
        self.location = None
        self.deployed_index_id = None
        self.index_endpoint_id = None

    def _init_endpoint(self, cfg: RequestContext):
        if aiplatform is None:
            raise VectorStoreConfigError("google-cloud-aiplatform not installed for Vertex vector search")
        if not self.project or not self.index_endpoint_id:
            raise VectorStoreConfigError("VECTOR_PROJECT_ID/GCP_PROJECT_ID and VECTOR_ENDPOINT_ID are required")
        aiplatform.init(project=self.project, location=self.location)
        endpoint_id = str(self.index_endpoint_id)
        if endpoint_id.startswith("projects/"):
            endpoint_name = endpoint_id
        else:
            endpoint_name = f"projects/{self.project}/locations/{self.location}/indexEndpoints/{endpoint_id}"
        return aiplatform.MatchingEngineIndexEndpoint(index_endpoint_name=endpoint_name)

    def _init_index(self):
        if aiplatform is None:
            raise VectorStoreConfigError("google-cloud-aiplatform not installed for Vertex vector search")
        index_id = getattr(self, "index_id", None) or runtime_config.get_vector_index_id()
        if not self.project or not index_id:
            raise VectorStoreConfigError("VECTOR_INDEX_ID (index resource or id) is required")
        idx_id_str = str(index_id)
        if idx_id_str.startswith("projects/"):
            index_name = idx_id_str
        else:
            index_name = f"projects/{self.project}/locations/{self.location}/indexes/{idx_id_str}"
        return aiplatform.MatchingEngineIndex(index_name=index_name)

    def _derive_deployed_index_id(self) -> Optional[str]:
        try:
            deployed = getattr(self._endpoint, "deployed_indexes", None) or []
            first = deployed[0] if deployed else None
            if first:
                return getattr(first, "id", None) or getattr(first, "deployed_index_id", None)
        except Exception:
            return None
        return None

    def upsert(
        self,
        item_id: str,
        vector: Sequence[float],
        tenant_id: str,
        env: str,
        space: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._ensure_backend(RequestContext(request_id="selecta", tenant_id=tenant_id, env=env))
        # Vertex expect list of IndexDatapoint objects or dicts
        
        datapoint = {
            "datapoint_id": item_id,
            "feature_vector": list(vector),
            "restricts": [
                {"namespace": "tenant_id", "allow_list": [tenant_id]},
                {"namespace": "env", "allow_list": [env]},
                {"namespace": "space", "allow_list": [space]},
            ],
            "crowding_tag": {"crowding_attribute": space}, # Optional optimization
        }
        # attributes field removed as it causes proto errors if not strictly typed

        try:
            self._index.upsert_datapoints(
                datapoints=[datapoint]
                # timeout removed
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
        self._ensure_backend(RequestContext(request_id="selecta", tenant_id=tenant_id, env=env))
        # Refactor: Pass simple queries + separate filter to avoid Proto coercion bugs
        queries = [list(vector)]
        
        # Filter structure for 'filter' arg in find_neighbors:
        # Often expects List[Namespace] objects or dicts matching Namespace proto (name, allow_tokens)
        vertex_filters = [
            Namespace(name="tenant_id", allow_tokens=[tenant_id]),
            Namespace(name="env", allow_tokens=[env]),
            Namespace(name="space", allow_tokens=[space]),
        ]

        deployed_id = self.deployed_index_id
        if not deployed_id:
             raise VectorStoreConfigError("No deployed_index_id available for query")

        try:
            response = self._endpoint.find_neighbors(
                deployed_index_id=deployed_id,
                queries=queries,
                num_neighbors=top_k,
                filter=vertex_filters
                # timeout removed
            )
        except Exception as exc:
            raise VectorStoreConfigError(f"Vertex query failed: {exc}") from exc
            
        # Response is list(list(MatchNeighbor)). We took 1 query.
        if not response:
            return []
            
        neighbors = response[0] # first query results
        return self._parse_neighbors(neighbors)

    def _parse_neighbors(self, neighbors: Any) -> List[ExplorerVectorHit]:
        hits: List[ExplorerVectorHit] = []
        # neighbors is a list of MatchNeighbor objects
        for neighbor in neighbors:
            
            doc_id = getattr(neighbor, "id", "")
            score = getattr(neighbor, "distance", 0.0)
            
            hits.append(ExplorerVectorHit(id=str(doc_id), score=float(score), metadata={}))
            
        return hits

    def query_by_datapoint_id(
        self,
        anchor_id: str,
        tenant_id: str,
        env: str,
        space: str,
        top_k: int = 10,
    ) -> List[ExplorerVectorHit]:
        raise NotImplementedError("query_by_datapoint_id not explicitly supported in this strict adapter yet.")

    def _ensure_backend(self, ctx: RequestContext) -> None:
        ensure_billable_vertex_allowed("Vertex Explorer vector backend")
        if getattr(self, "_endpoint", None) and getattr(self, "_index", None):
            return
        vs_cfg = self._selecta.vector_store_config(ctx)
        self.project = vs_cfg.project or runtime_config.get_firestore_project()
        self.location = vs_cfg.region or runtime_config.get_env_region_fallback()
        self.index_endpoint_id = vs_cfg.endpoint_id
        self.index_id = vs_cfg.index_id
        self._endpoint = self._endpoint or self._init_endpoint(ctx)
        self._index = self._init_index()
        if not self.deployed_index_id:
            self.deployed_index_id = self._derive_deployed_index_id()
        if not self.deployed_index_id:
            raise VectorStoreConfigError("Deployed index id is required for queries")
