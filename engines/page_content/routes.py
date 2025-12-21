from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends

from engines.common.identity import RequestContext, assert_context_matches, get_request_context
from engines.identity.auth import get_auth_context, require_tenant_membership, require_tenant_role
from engines.page_content.models import PageContent
from engines.page_content.service import get_page_content_service

router = APIRouter(prefix="/pages", tags=["pages"])


@router.post("")
def create_page(
    payload: PageContent,
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_role(auth, context.tenant_id, ["owner", "admin"])
    assert_context_matches(context, payload.tenant_id, payload.env)
    return get_page_content_service().create_page(context, payload)


@router.get("")
def list_pages(
    surface: Optional[str] = None,
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_membership(auth, context.tenant_id)
    return get_page_content_service().list_pages(context, surface)


@router.get("/{page_id}")
def get_page(
    page_id: str,
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_membership(auth, context.tenant_id)
    return get_page_content_service().get_page(context, page_id)


@router.patch("/{page_id}")
def update_page(
    page_id: str,
    payload: PageContent,
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_role(auth, context.tenant_id, ["owner", "admin"])
    return get_page_content_service().update_page(context, page_id, payload)


@router.post("/{page_id}/publish")
def publish_page(
    page_id: str,
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_role(auth, context.tenant_id, ["owner", "admin"])
    return get_page_content_service().publish_page(context, page_id)


@router.delete("/{page_id}")
def delete_page(
    page_id: str,
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_role(auth, context.tenant_id, ["owner", "admin"])
    get_page_content_service().delete_page(context, page_id)
    return {"status": "deleted"}
