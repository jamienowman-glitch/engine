"""HTTP routes that expose the knowledge store."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from typing import Any

from engines.common.identity import RequestContext, get_request_context
from engines.identity.auth import get_auth_context, require_tenant_membership
from engines.knowledge.schemas import KnowledgeIngestRequest, KnowledgeQueryRequest
from engines.knowledge.service import KnowledgeService

router = APIRouter()
_service: KnowledgeService | None = None


def _get_service() -> KnowledgeService:
    global _service
    if _service is None:
        _service = KnowledgeService()
    return _service


@router.post("/knowledge/ingest")
def ingest_document(
    request: KnowledgeIngestRequest,
    ctx: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
) -> dict[str, str]:
    """Ingest raw text into RAW_BUCKET and index metadata."""
    require_tenant_membership(auth, ctx.tenant_id)
    return _get_service().ingest(ctx, request)


@router.post("/knowledge/query")
def query_documents(
    request: KnowledgeQueryRequest,
    ctx: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
) -> dict[str, list[dict[str, Any]]]:
    """Query the cached knowledge documents."""
    require_tenant_membership(auth, ctx.tenant_id)
    return {"results": _get_service().query(ctx, request)}
