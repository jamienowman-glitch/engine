"""Canvas Router (EN-04).

Exposes /canvas endpoints.
"""
from __future__ import annotations

import logging
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from engines.common.identity import RequestContext, get_request_context
from engines.identity.auth import AuthContext, get_auth_context, require_tenant_membership
from engines.common.error_envelope import error_response
from engines.canvas_reducer import CanvasState

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/canvas", tags=["canvas"])

class TokenCatalogPayload(BaseModel):
    """Response for /canvas/{id}/token_catalog."""
    canvas_id: str
    head_rev: int
    elements: List[Dict[str, Any]] = Field(default_factory=list)
    schemas: Dict[str, Any] = Field(default_factory=dict)
    values: Dict[str, Any] = Field(default_factory=dict)

# Mock service dependency for now, until we have full integration
class CanvasService:
    def get_snapshot(self, context: RequestContext, canvas_id: str) -> Optional[CanvasState]:
        # TODO: Implement real storage retrieval
        # For now, return empty or mock state
        return CanvasState()

    def get_head_rev(self, context: RequestContext, canvas_id: str) -> int:
        return 0

_canvas_service = CanvasService()

def get_canvas_service() -> CanvasService:
    return _canvas_service

def set_canvas_service(service: CanvasService):
    global _canvas_service
    _canvas_service = service


@router.get("/{canvas_id}/token_catalog", response_model=TokenCatalogPayload)
def get_token_catalog(
    canvas_id: str,
    context: RequestContext = Depends(get_request_context),
    auth: AuthContext = Depends(get_auth_context),
    service: CanvasService = Depends(get_canvas_service),
):
    """Get token catalog for a canvas (EN-04)."""
    try:
        require_tenant_membership(auth, context.tenant_id)
    except HTTPException as exc:
        error_response(
            code="auth.tenant_membership_required",
            message=str(exc.detail),
            status_code=exc.status_code,
            resource_kind="canvas",
        )

    state = service.get_snapshot(context, canvas_id)
    if not state:
        error_response(
            code="canvas.not_found",
            message=f"Canvas {canvas_id} not found",
            status_code=404,
            resource_kind="canvas",
        )

    head_rev = service.get_head_rev(context, canvas_id)

    # Flatten state into elements list
    elements = []

    # Nodes
    for node in state.nodes.values():
        elements.append({
            "id": node.id,
            "type": node.type,
            "category": "node",
            "data": node.data
        })

    # Edges
    for edge in state.edges.values():
        elements.append({
            "id": edge.id,
            "source": edge.source,
            "target": edge.target,
            "category": "edge",
            "data": edge.data
        })

    # Tokens (values)
    values = {}
    for token in state.tokens.values():
        values[token.id] = token.value

    # Schemas (stub)
    schemas = {}

    return TokenCatalogPayload(
        canvas_id=canvas_id,
        head_rev=head_rev,
        elements=elements,
        schemas=schemas,
        values=values
    )
