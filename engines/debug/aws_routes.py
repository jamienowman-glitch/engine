from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from engines.common.aws_runtime import aws_billing_probe, aws_healthcheck
from engines.common.identity import RequestContext, get_request_context
from engines.identity.auth import get_auth_context, require_tenant_role, require_tenant_membership

router = APIRouter(prefix="/debug", tags=["debug"])


@router.get("/aws-identity")
def aws_identity_debug(
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_membership(auth, context.tenant_id)
    require_tenant_role(auth, context.tenant_id, ["owner", "admin"])
    try:
        return aws_healthcheck()
    except Exception as exc:
        raise HTTPException(status_code=503, detail={"error": "aws_identity_failed", "message": str(exc)})


@router.get("/aws-billing-probe")
def aws_billing_probe_debug(
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_membership(auth, context.tenant_id)
    require_tenant_role(auth, context.tenant_id, ["owner", "admin"])
    result = aws_billing_probe()
    if result.get("ok"):
        return result
    # Surface as 200 with ok=false for observability without failing health
    return result
