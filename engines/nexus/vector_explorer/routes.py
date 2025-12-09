"""HTTP routes for Vector Explorer."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from engines.nexus.embedding import VertexEmbeddingAdapter
from engines.nexus.vector_explorer.repository import FirestoreVectorCorpusRepository
from engines.nexus.vector_explorer.schemas import QueryMode, VectorExplorerQuery
from engines.nexus.vector_explorer.service import VectorExplorerService
from engines.nexus.vector_explorer.vector_store import VectorStoreConfigError, VertexExplorerVectorStore

router = APIRouter()

_service: VectorExplorerService | None = None


def _get_service() -> VectorExplorerService:
    global _service
    if _service is None:
        _service = VectorExplorerService(
            repository=FirestoreVectorCorpusRepository(),
            vector_store=VertexExplorerVectorStore(),
            embedder=VertexEmbeddingAdapter(),
        )
    return _service


@router.get("/vector-explorer/scene")
def get_vector_scene(
    tenant_id: str = Query(..., pattern=r"^t_[a-z0-9_-]+$"),
    env: str = Query(...),
    space: str = Query(...),
    query_mode: QueryMode = QueryMode.all,
    limit: int = Query(20, ge=1, le=200),
    tags: Optional[str] = None,
    anchor_id: Optional[str] = None,
    query_text: Optional[str] = None,
):
    q = VectorExplorerQuery(
        tenant_id=tenant_id,
        env=env,
        space=space,
        tags=[t for t in (tags.split(",") if tags else []) if t],
        query_mode=query_mode,
        limit=limit,
        anchor_id=anchor_id,
        query_text=query_text,
    )
    try:
        service = _get_service()
        scene = service.build_scene_from_query(q)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except (VectorStoreConfigError, RuntimeError) as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return scene
