from __future__ import annotations

from typing import List, Optional

from engines.common.identity import RequestContext
from engines.common.surface_normalizer import normalize_surface_id
from engines.kpi.models import KpiCorridor, KpiDefinition, KpiRawMeasurement, SurfaceKpiSet, KpiCategory, KpiType
from engines.kpi.repository import FileKpiRepository, KpiRepository


def _default_repo() -> KpiRepository:
    """Get KPI repository via routing registry if available, fallback to filesystem.
    
    Lane 3 wiring: Routes metrics_store resource_kind through routing registry
    for raw measurement persistence. Definitions/corridors remain filesystem-based.
    """
    try:
        from engines.routing.registry import routing_registry
        from engines.config import runtime_config
        
        registry = routing_registry()
        route = registry.get_route(
            resource_kind="metrics_store",
            tenant_id="t_system",
            env=runtime_config.env_name(),
            project_id="p_internal",
        )
        
        if route:
            # Route exists; use filesystem KPI repo
            # Raw measurements will be stored in metrics_store via FileKpiRepository
            return FileKpiRepository()
    except Exception:
        # Fallback to filesystem if routing fails
        pass
    
    return FileKpiRepository()


def _resolve_surface(surface: Optional[str], fallback: Optional[str] = None) -> Optional[str]:
    candidate = surface or fallback
    return normalize_surface_id(candidate)


kpi_repo: KpiRepository = _default_repo()


class KpiService:
    def __init__(self, repo: Optional[KpiRepository] = None) -> None:
        self.repo = repo or kpi_repo

    # Registry Metadata
    def create_category(self, ctx: RequestContext, payload: KpiCategory) -> KpiCategory:
        payload.tenant_id = ctx.tenant_id
        payload.env = ctx.env
        return self.repo.create_category(payload)

    def list_categories(self, ctx: RequestContext) -> List[KpiCategory]:
        return self.repo.list_categories(ctx.tenant_id, ctx.env)

    def create_type(self, ctx: RequestContext, payload: KpiType) -> KpiType:
        payload.tenant_id = ctx.tenant_id
        payload.env = ctx.env
        return self.repo.create_type(payload)

    def list_types(self, ctx: RequestContext) -> List[KpiType]:
        return self.repo.list_types(ctx.tenant_id, ctx.env)

    def create_definition(self, ctx: RequestContext, payload: KpiDefinition) -> KpiDefinition:
        payload.tenant_id = ctx.tenant_id
        payload.env = ctx.env
        payload.surface = _resolve_surface(payload.surface, ctx.surface_id)
        return self.repo.create_definition(payload)

    def list_definitions(self, ctx: RequestContext, surface: Optional[str]) -> List[KpiDefinition]:
        surface_value = _resolve_surface(surface, ctx.surface_id)
        return self.repo.list_definitions(ctx.tenant_id, ctx.env, surface=surface_value)

    def upsert_corridor(self, ctx: RequestContext, payload: KpiCorridor) -> KpiCorridor:
        payload.tenant_id = ctx.tenant_id
        payload.env = ctx.env
        payload.surface = _resolve_surface(payload.surface, ctx.surface_id)
        return self.repo.upsert_corridor(payload)

    def list_corridors(self, ctx: RequestContext, surface: Optional[str]) -> List[KpiCorridor]:
        surface_value = _resolve_surface(surface, ctx.surface_id)
        return self.repo.list_corridors(ctx.tenant_id, ctx.env, surface=surface_value)

    def get_corridor_by_kpi(self, tenant_id: str, env: str, surface: Optional[str], kpi_name: str) -> Optional[KpiCorridor]:
        surface_value = _resolve_surface(surface)
        return self.repo.get_corridor_by_kpi(tenant_id, env, surface_value, kpi_name)

    def upsert_surface_kpi_set(self, ctx: RequestContext, payload: SurfaceKpiSet) -> SurfaceKpiSet:
        payload.tenant_id = ctx.tenant_id
        payload.env = ctx.env
        payload.surface = _resolve_surface(payload.surface, ctx.surface_id)
        return self.repo.upsert_surface_kpi_set(payload)

    def list_surface_kpi_sets(self, ctx: RequestContext, surface: Optional[str]) -> List[SurfaceKpiSet]:
        surface_value = _resolve_surface(surface, ctx.surface_id)
        return self.repo.list_surface_kpi_sets(ctx.tenant_id, ctx.env, surface=surface_value)

    def get_surface_kpi_set(self, ctx: RequestContext, surface: str) -> Optional[SurfaceKpiSet]:
        surface_value = _resolve_surface(surface, ctx.surface_id)
        if surface_value is None:
            return None
        return self.repo.get_surface_kpi_set(ctx.tenant_id, ctx.env, surface_value)

    def record_raw_measurement(self, ctx: RequestContext, payload: KpiRawMeasurement) -> KpiRawMeasurement:
        payload.tenant_id = ctx.tenant_id
        payload.env = ctx.env
        payload.surface = _resolve_surface(payload.surface, ctx.surface_id)
        return self.repo.record_raw_measurement(payload)

    def list_raw_measurements(
        self,
        ctx: RequestContext,
        surface: Optional[str] = None,
        kpi_name: Optional[str] = None,
        limit: int = 20,
    ) -> List[KpiRawMeasurement]:
        surface_value = _resolve_surface(surface, ctx.surface_id)
        return self.repo.list_raw_measurements(ctx.tenant_id, ctx.env, surface=surface_value, kpi_name=kpi_name, limit=limit)

    def latest_raw_measurement(self, ctx: RequestContext, surface: str, kpi_name: str) -> Optional[KpiRawMeasurement]:
        surface_value = _resolve_surface(surface, ctx.surface_id)
        if surface_value is None:
            return None
        return self.repo.latest_raw_measurement(ctx.tenant_id, ctx.env, surface_value, kpi_name)


_default_service: Optional[KpiService] = None


def get_kpi_service() -> KpiService:
    global _default_service
    if _default_service is None:
        _default_service = KpiService()
    return _default_service


def set_kpi_service(service: KpiService) -> None:
    global _default_service, kpi_repo
    _default_service = service
    kpi_repo = service.repo
