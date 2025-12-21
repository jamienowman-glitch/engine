from __future__ import annotations

from typing import Dict, List, Optional, Protocol

from engines.kpi.models import KpiCorridor, KpiDefinition


class KpiRepository(Protocol):
    def create_definition(self, definition: KpiDefinition) -> KpiDefinition: ...
    def list_definitions(self, tenant_id: str, env: str, surface: Optional[str] = None) -> List[KpiDefinition]: ...
    def upsert_corridor(self, corridor: KpiCorridor) -> KpiCorridor: ...
    def list_corridors(self, tenant_id: str, env: str, surface: Optional[str] = None) -> List[KpiCorridor]: ...
    def get_corridor(self, tenant_id: str, env: str, corridor_id: str) -> Optional[KpiCorridor]: ...
    def get_corridor_by_kpi(self, tenant_id: str, env: str, surface: Optional[str], kpi_name: str) -> Optional[KpiCorridor]: ...


class InMemoryKpiRepository:
    def __init__(self) -> None:
        self._defs: Dict[tuple[str, str, str], KpiDefinition] = {}
        self._corridors: Dict[tuple[str, str, str], KpiCorridor] = {}

    def create_definition(self, definition: KpiDefinition) -> KpiDefinition:
        key = (definition.tenant_id, definition.env, definition.id)
        self._defs[key] = definition
        return definition

    def list_definitions(self, tenant_id: str, env: str, surface: Optional[str] = None) -> List[KpiDefinition]:
        defs = [d for (t, e, _), d in self._defs.items() if t == tenant_id and e == env]
        if surface:
            defs = [d for d in defs if d.surface == surface]
        return defs

    def upsert_corridor(self, corridor: KpiCorridor) -> KpiCorridor:
        key = (corridor.tenant_id, corridor.env, corridor.id)
        self._corridors[key] = corridor
        return corridor

    def list_corridors(self, tenant_id: str, env: str, surface: Optional[str] = None) -> List[KpiCorridor]:
        corridors = [c for (t, e, _), c in self._corridors.items() if t == tenant_id and e == env]
        if surface:
            corridors = [c for c in corridors if c.surface == surface]
        return corridors

    def get_corridor(self, tenant_id: str, env: str, corridor_id: str) -> Optional[KpiCorridor]:
        return self._corridors.get((tenant_id, env, corridor_id))

    def get_corridor_by_kpi(self, tenant_id: str, env: str, surface: Optional[str], kpi_name: str) -> Optional[KpiCorridor]:
        for c in self.list_corridors(tenant_id, env, surface=surface):
            if c.kpi_name == kpi_name:
                return c
        return None


class FirestoreKpiRepository(InMemoryKpiRepository):
    """Placeholder for Firestore implementation."""

    def __init__(self, *args, **kwargs):  # pragma: no cover - stub
        raise NotImplementedError("FirestoreKpiRepository not implemented yet")
