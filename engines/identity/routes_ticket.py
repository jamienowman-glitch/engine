from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from engines.common.identity import RequestContext, get_request_context
from engines.identity.auth import AuthContext, get_auth_context
from engines.identity.ticket_service import (
    TICKET_TTL_SECONDS,
    TicketError,
    issue_ticket,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/ticket")
def issue_auth_ticket(
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    try:
        token = issue_ticket(
            {
                "tenant_id": request_context.tenant_id,
                "mode": request_context.mode,
                "project_id": request_context.project_id,
                "surface_id": request_context.surface_id,
                "app_id": request_context.app_id,
                "user_id": request_context.user_id or auth_context.user_id,
                "request_id": request_context.request_id,
            }
        )
    except TicketError as exc:
        status = 500 if "ENGINES_TICKET_SECRET" in str(exc) else 400
        raise HTTPException(status_code=status, detail=str(exc))
    return {"ticket": token, "expires_in": TICKET_TTL_SECONDS}
