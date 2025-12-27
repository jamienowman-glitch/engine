from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from engines.billing.models import CheckoutSessionRequest
from engines.billing.service import BillingError, get_billing_service
from engines.common.identity import RequestContext, get_request_context
from engines.identity.auth import get_auth_context, require_tenant_role

router = APIRouter(prefix="/billing", tags=["billing"])


@router.post("/checkout-session")
def create_checkout_session(
    payload: CheckoutSessionRequest,
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_role(auth, context.tenant_id, ["owner", "admin"])
    svc = get_billing_service()
    try:
        session = svc.create_checkout_session(context, payload)
        return session
    except BillingError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/webhook")
async def stripe_webhook(request: Request):
    # INTENTIONALLY_PUBLIC: Stripe webhook signature validation provides protection
    # (Stripe sends HMAC-SHA256 signature in Stripe-Signature header; we verify against webhook secret)
    signature = request.headers.get("Stripe-Signature")
    if not signature:
        raise HTTPException(status_code=400, detail="missing_signature")
    payload = (await request.body()).decode("utf-8")
    svc = get_billing_service()
    try:
        return svc.handle_webhook(signature, payload)
    except BillingError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
