"""Repositories for temperature configs and snapshots."""
from __future__ import annotations

from typing import Dict, List, Optional, Protocol

from engines.temperature.models import CeilingConfig, FloorConfig, TemperatureSnapshot, TemperatureWeights


class TemperatureRepository(Protocol):
    def upsert_floor(self, cfg: FloorConfig) -> FloorConfig: ...
    def upsert_ceiling(self, cfg: CeilingConfig) -> CeilingConfig: ...
    def upsert_weights(self, cfg: TemperatureWeights) -> TemperatureWeights: ...

    def get_floor(self, tenant_id: str, env: str, surface: str) -> Optional[FloorConfig]: ...
    def get_ceiling(self, tenant_id: str, env: str, surface: str) -> Optional[CeilingConfig]: ...
    def get_weights(self, tenant_id: str, env: str, surface: str) -> Optional[TemperatureWeights]: ...

    def save_snapshot(self, snap: TemperatureSnapshot) -> TemperatureSnapshot: ...
    def list_snapshots(self, tenant_id: str, env: str, surface: str, limit: int = 20, offset: int = 0) -> List[TemperatureSnapshot]: ...


class InMemoryTemperatureRepository:
    def __init__(self) -> None:
        self._floors: Dict[tuple[str, str, str], FloorConfig] = {}
        self._ceilings: Dict[tuple[str, str, str], CeilingConfig] = {}
        self._weights: Dict[tuple[str, str, str], TemperatureWeights] = {}
        self._snapshots: Dict[tuple[str, str, str], List[TemperatureSnapshot]] = {}

    def _key(self, tenant_id: str, env: str, surface: str) -> tuple[str, str, str]:
        return (tenant_id, env, surface)

    def upsert_floor(self, cfg: FloorConfig) -> FloorConfig:
        self._floors[self._key(cfg.tenant_id, cfg.env, cfg.surface)] = cfg
        return cfg

    def upsert_ceiling(self, cfg: CeilingConfig) -> CeilingConfig:
        self._ceilings[self._key(cfg.tenant_id, cfg.env, cfg.surface)] = cfg
        return cfg

    def upsert_weights(self, cfg: TemperatureWeights) -> TemperatureWeights:
        self._weights[self._key(cfg.tenant_id, cfg.env, cfg.surface)] = cfg
        return cfg

    def get_floor(self, tenant_id: str, env: str, surface: str) -> Optional[FloorConfig]:
        return self._floors.get(self._key(tenant_id, env, surface))

    def get_ceiling(self, tenant_id: str, env: str, surface: str) -> Optional[CeilingConfig]:
        return self._ceilings.get(self._key(tenant_id, env, surface))

    def get_weights(self, tenant_id: str, env: str, surface: str) -> Optional[TemperatureWeights]:
        return self._weights.get(self._key(tenant_id, env, surface))

    def save_snapshot(self, snap: TemperatureSnapshot) -> TemperatureSnapshot:
        key = self._key(snap.tenant_id, snap.env, snap.surface)
        self._snapshots.setdefault(key, []).insert(0, snap)
        return snap

    def list_snapshots(self, tenant_id: str, env: str, surface: str, limit: int = 20, offset: int = 0) -> List[TemperatureSnapshot]:
        key = self._key(tenant_id, env, surface)
        items = self._snapshots.get(key, [])
        return items[offset : offset + limit]

