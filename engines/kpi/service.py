from __future__ import annotations

from typing import List, Optional

from fastapi import HTTPException

from engines.common.identity import RequestContext
from engines.kpi.models import KpiCorridor, KpiDefinition
from engines.kpi.repository import InMemoryKpiRepository, KpiRepository, FirestoreKpiRepository
import os


def _default_repo() -> KpiRepository:
    backend = os.getenv("KPI_BACKEND", "").lower()
    if backend == "firestore":
        try:
            return FirestoreKpiRepository()
        except Exception:
            return InMemoryKpiRepository()
    return InMemoryKpiRepository()


kpi_repo: KpiRepository = _default_repo()


class KpiService:
    def __init__(self, repo: Optional[KpiRepository] = None) -> None:
        self.repo = repo or kpi_repo

    def create_definition(self, ctx: RequestContext, payload: KpiDefinition) -> KpiDefinition:
        payload.tenant_id = ctx.tenant_id
        payload.env = ctx.env
        return self.repo.create_definition(payload)

    def list_definitions(self, ctx: RequestContext, surface: Optional[str]) -> List[KpiDefinition]:
        return self.repo.list_definitions(ctx.tenant_id, ctx.env, surface=surface)

    def upsert_corridor(self, ctx: RequestContext, payload: KpiCorridor) -> KpiCorridor:
        payload.tenant_id = ctx.tenant_id
        payload.env = ctx.env
        return self.repo.upsert_corridor(payload)

    def list_corridors(self, ctx: RequestContext, surface: Optional[str]) -> List[KpiCorridor]:
        return self.repo.list_corridors(ctx.tenant_id, ctx.env, surface=surface)

    def get_corridor_by_kpi(self, tenant_id: str, env: str, surface: Optional[str], kpi_name: str) -> Optional[KpiCorridor]:
        return self.repo.get_corridor_by_kpi(tenant_id, env, surface, kpi_name)


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
