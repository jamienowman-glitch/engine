"""Repositories for temperature configs and snapshots."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Protocol

from pydantic import BaseModel

from engines.common.surface_normalizer import normalize_surface_id
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


class FileTemperatureRepository(TemperatureRepository):
    def __init__(self, root: Optional[str] = None) -> None:
        self._root = Path(root or Path("var") / "temperature")
        self._root.mkdir(parents=True, exist_ok=True)

    def _surface_key(self, surface: Optional[str]) -> str:
        normalized = normalize_surface_id(surface)
        return normalized or "_default"

    def _surface_dir(self, tenant_id: str, env: str, surface: Optional[str]) -> Path:
        surface_token = self._surface_key(surface)
        path = self._root / tenant_id / env / surface_token
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _json_file(self, tenant_id: str, env: str, surface: Optional[str], name: str) -> Path:
        return self._surface_dir(tenant_id, env, surface) / name

    def _snapshots_file(self, tenant_id: str, env: str, surface: Optional[str]) -> Path:
        return self._json_file(tenant_id, env, surface, "snapshots.jsonl")

    @staticmethod
    def _write_json(path: Path, value: BaseModel) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fh:
            fh.write(value.model_dump_json())

    @staticmethod
    def _read_json(path: Path, model: type[BaseModel]) -> Optional[BaseModel]:
        if not path.exists():
            return None
        return model.parse_raw(path.read_text(encoding="utf-8"))

    @staticmethod
    def _append_jsonl(path: Path, value: BaseModel) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(value.model_dump_json() + "\n")

    @staticmethod
    def _read_jsonl(path: Path, model: type[BaseModel]) -> List[BaseModel]:
        if not path.exists():
            return []
        items: List[BaseModel] = []
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                raw = line.strip()
                if not raw:
                    continue
                items.append(model.parse_raw(raw))
        return items

    def upsert_floor(self, cfg: FloorConfig) -> FloorConfig:
        self._write_json(self._json_file(cfg.tenant_id, cfg.env, cfg.surface, "floors.json"), cfg)
        return cfg

    def upsert_ceiling(self, cfg: CeilingConfig) -> CeilingConfig:
        self._write_json(self._json_file(cfg.tenant_id, cfg.env, cfg.surface, "ceilings.json"), cfg)
        return cfg

    def upsert_weights(self, cfg: TemperatureWeights) -> TemperatureWeights:
        self._write_json(self._json_file(cfg.tenant_id, cfg.env, cfg.surface, "weights.json"), cfg)
        return cfg

    def get_floor(self, tenant_id: str, env: str, surface: str) -> Optional[FloorConfig]:
        path = self._json_file(tenant_id, env, surface, "floors.json")
        return self._read_json(path, FloorConfig)

    def get_ceiling(self, tenant_id: str, env: str, surface: str) -> Optional[CeilingConfig]:
        path = self._json_file(tenant_id, env, surface, "ceilings.json")
        return self._read_json(path, CeilingConfig)

    def get_weights(self, tenant_id: str, env: str, surface: str) -> Optional[TemperatureWeights]:
        path = self._json_file(tenant_id, env, surface, "weights.json")
        return self._read_json(path, TemperatureWeights)

    def save_snapshot(self, snap: TemperatureSnapshot) -> TemperatureSnapshot:
        self._append_jsonl(self._snapshots_file(snap.tenant_id, snap.env, snap.surface), snap)
        return snap

    def list_snapshots(self, tenant_id: str, env: str, surface: str, limit: int = 20, offset: int = 0) -> List[TemperatureSnapshot]:
        records = self._read_jsonl(self._snapshots_file(tenant_id, env, surface), TemperatureSnapshot)
        records.sort(key=lambda snap: snap.created_at, reverse=True)
        return records[offset : offset + limit]
