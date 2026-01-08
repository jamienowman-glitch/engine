from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Query, HTTPException

from engines.common.identity import RequestContext, get_request_context
from engines.common.error_envelope import error_response
from engines.identity.auth import get_auth_context, require_tenant_membership, require_tenant_role
from engines.kpi.models import KpiCategory, KpiType
from engines.kpi.service import KpiService, get_kpi_service

router = APIRouter(prefix="/registry/kpi", tags=["kpi-registry"])

@router.get("/categories", response_model=List[KpiCategory])
def list_categories(
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
    service: KpiService = Depends(get_kpi_service),
) -> List[KpiCategory]:
    require_tenant_membership(auth, context.tenant_id)
    try:
        return service.list_categories(context)
    except Exception as exc:
        error_response(
            code="kpi.registry_read_failed",
            message=str(exc),
            status_code=500,
            resource_kind="kpi_registry",
        )

@router.post("/categories", response_model=KpiCategory)
def create_category(
    payload: KpiCategory,
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
    service: KpiService = Depends(get_kpi_service),
) -> KpiCategory:
    require_tenant_role(auth, context.tenant_id, ["owner", "admin"])
    try:
        return service.create_category(context, payload)
    except Exception as exc:
        error_response(
            code="kpi.registry_write_failed",
            message=str(exc),
            status_code=500,
            resource_kind="kpi_registry",
        )

@router.get("/types", response_model=List[KpiType])
def list_types(
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
    service: KpiService = Depends(get_kpi_service),
) -> List[KpiType]:
    require_tenant_membership(auth, context.tenant_id)
    try:
        return service.list_types(context)
    except Exception as exc:
        error_response(
            code="kpi.registry_read_failed",
            message=str(exc),
            status_code=500,
            resource_kind="kpi_registry",
        )

@router.post("/types", response_model=KpiType)
def create_type(
    payload: KpiType,
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
    service: KpiService = Depends(get_kpi_service),
) -> KpiType:
    require_tenant_role(auth, context.tenant_id, ["owner", "admin"])
    try:
        return service.create_type(context, payload)
    except Exception as exc:
        error_response(
            code="kpi.registry_write_failed",
            message=str(exc),
            status_code=500,
            resource_kind="kpi_registry",
        )
