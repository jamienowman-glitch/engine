from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query

from engines.common.identity import RequestContext, assert_context_matches, get_request_context
from engines.identity.auth import get_auth_context, require_tenant_membership, require_tenant_role
from engines.kpi.models import KpiCorridor, KpiDefinition, KpiRawMeasurement, SurfaceKpiSet
from engines.kpi.service import get_kpi_service
from engines.strategy_lock.service import get_strategy_lock_service

router = APIRouter(prefix="/kpi", tags=["kpi"])


@router.post("/definitions")
def create_definition(
    payload: KpiDefinition,
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_role(auth, context.tenant_id, ["owner", "admin"])
    assert_context_matches(context, payload.tenant_id, payload.env)
    return get_kpi_service().create_definition(context, payload)


@router.get("/definitions")
def list_definitions(
    surface: Optional[str] = None,
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_membership(auth, context.tenant_id)
    return get_kpi_service().list_definitions(context, surface)


@router.put("/corridors")
def upsert_corridor(
    payload: KpiCorridor,
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_role(auth, context.tenant_id, ["owner", "admin"])
    assert_context_matches(context, payload.tenant_id, payload.env)
    get_strategy_lock_service().require_strategy_lock_or_raise(context, payload.surface, "kpi:corridor_upsert")
    return get_kpi_service().upsert_corridor(context, payload)


@router.get("/corridors")
def list_corridors(
    surface: Optional[str] = None,
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_membership(auth, context.tenant_id)
    return get_kpi_service().list_corridors(context, surface)


@router.get("/config")
def get_kpi_config_bundle(
    surface: Optional[str] = None,
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_membership(auth, context.tenant_id)
    defs = get_kpi_service().list_definitions(context, surface)
    corridors = get_kpi_service().list_corridors(context, surface)
    surface_sets = get_kpi_service().list_surface_kpi_sets(context, surface)
    return {"definitions": defs, "corridors": corridors, "surface_kpis": surface_sets}


@router.put("/surface-kpis")
def upsert_surface_kpis(
    payload: SurfaceKpiSet,
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_role(auth, context.tenant_id, ["owner", "admin"])
    assert_context_matches(context, payload.tenant_id, payload.env)
    get_strategy_lock_service().require_strategy_lock_or_raise(context, payload.surface, "kpi:surface_kpi_upsert")
    return get_kpi_service().upsert_surface_kpi_set(context, payload)


@router.get("/surface-kpis")
def list_surface_kpis(
    surface: Optional[str] = None,
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_membership(auth, context.tenant_id)
    return get_kpi_service().list_surface_kpi_sets(context, surface)


@router.post("/raw")
def record_raw_measurement(
    payload: KpiRawMeasurement,
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_membership(auth, context.tenant_id)
    assert_context_matches(context, payload.tenant_id, payload.env)
    return get_kpi_service().record_raw_measurement(context, payload)


@router.get("/raw")
def list_raw_measurements(
    surface: Optional[str] = None,
    kpi_name: Optional[str] = None,
    limit: int = Query(20, ge=1, le=200),
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_membership(auth, context.tenant_id)
    return get_kpi_service().list_raw_measurements(context, surface=surface, kpi_name=kpi_name, limit=limit)
