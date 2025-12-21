from __future__ import annotations

from fastapi import APIRouter, Depends

from engines.analytics_events.models import CtaClickEvent, PageViewEvent
from engines.analytics_events.service import get_analytics_events_service
from engines.common.identity import RequestContext, get_request_context
from engines.identity.auth import get_auth_context, require_tenant_membership

router = APIRouter(prefix="/analytics/events", tags=["analytics_events"])


@router.post("/pageview")
def record_page_view(
    payload: PageViewEvent,
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_membership(auth, context.tenant_id)
    return get_analytics_events_service().record_page_view(context, payload)


@router.post("/cta-click")
def record_cta_click(
    payload: CtaClickEvent,
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_membership(auth, context.tenant_id)
    return get_analytics_events_service().record_cta_click(context, payload)
