from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Protocol

from pydantic import BaseModel

from engines.common.surface_normalizer import normalize_surface_id
from engines.kpi.models import (
    KpiCorridor,
    KpiDefinition,
    KpiRawMeasurement,
    SurfaceKpiSet,
    KpiCategory,
    KpiType,
)


class KpiRepository(Protocol):
    # Registry Metadata
    def create_category(self, category: KpiCategory) -> KpiCategory: ...
    def list_categories(self, tenant_id: str, env: str) -> List[KpiCategory]: ...
    def create_type(self, kpi_type: KpiType) -> KpiType: ...
    def list_types(self, tenant_id: str, env: str) -> List[KpiType]: ...

    def create_definition(self, definition: KpiDefinition) -> KpiDefinition: ...
    def list_definitions(self, tenant_id: str, env: str, surface: Optional[str] = None) -> List[KpiDefinition]: ...
    def upsert_corridor(self, corridor: KpiCorridor) -> KpiCorridor: ...
    def list_corridors(self, tenant_id: str, env: str, surface: Optional[str] = None) -> List[KpiCorridor]: ...
    def get_corridor(self, tenant_id: str, env: str, corridor_id: str) -> Optional[KpiCorridor]: ...
    def get_corridor_by_kpi(self, tenant_id: str, env: str, surface: Optional[str], kpi_name: str) -> Optional[KpiCorridor]: ...
    def upsert_surface_kpi_set(self, surface_set: SurfaceKpiSet) -> SurfaceKpiSet: ...
    def list_surface_kpi_sets(self, tenant_id: str, env: str, surface: Optional[str] = None) -> List[SurfaceKpiSet]: ...
    def get_surface_kpi_set(self, tenant_id: str, env: str, surface: str) -> Optional[SurfaceKpiSet]: ...
    def record_raw_measurement(self, measurement: KpiRawMeasurement) -> KpiRawMeasurement: ...
    def list_raw_measurements(
        self,
        tenant_id: str,
        env: str,
        surface: Optional[str] = None,
        kpi_name: Optional[str] = None,
        limit: int = 20,
    ) -> List[KpiRawMeasurement]: ...
    def latest_raw_measurement(self, tenant_id: str, env: str, surface: str, kpi_name: str) -> Optional[KpiRawMeasurement]: ...


class InMemoryKpiRepository:
    def __init__(self) -> None:
        self._defs: Dict[tuple[str, str, str], KpiDefinition] = {}
        self._corridors: Dict[tuple[str, str, str], KpiCorridor] = {}
        self._surface_sets: Dict[tuple[str, str, Optional[str]], SurfaceKpiSet] = {}
        self._raw: Dict[tuple[str, str, Optional[str]], List[KpiRawMeasurement]] = {}
        self._categories: Dict[tuple[str, str, str], KpiCategory] = {}
        self._types: Dict[tuple[str, str, str], KpiType] = {}

    @staticmethod
    def _surface_key(surface: Optional[str]) -> Optional[str]:
        return normalize_surface_id(surface) if surface else None

    # Registry Metadata
    def create_category(self, category: KpiCategory) -> KpiCategory:
        key = (category.tenant_id, category.env, category.id or category.name)
        self._categories[key] = category
        return category

    def list_categories(self, tenant_id: str, env: str) -> List[KpiCategory]:
        return [c for (t, e, _), c in self._categories.items() if t == tenant_id and e == env]

    def create_type(self, kpi_type: KpiType) -> KpiType:
        key = (kpi_type.tenant_id, kpi_type.env, kpi_type.id or kpi_type.name)
        self._types[key] = kpi_type
        return kpi_type

    def list_types(self, tenant_id: str, env: str) -> List[KpiType]:
        return [t for (t, e, _), t in self._types.items() if t == tenant_id and e == env]

    def create_definition(self, definition: KpiDefinition) -> KpiDefinition:
        key = (definition.tenant_id, definition.env, definition.id)
        self._defs[key] = definition
        return definition

    def list_definitions(self, tenant_id: str, env: str, surface: Optional[str] = None) -> List[KpiDefinition]:
        surface_filter = self._surface_key(surface)
        defs = [d for (t, e, _), d in self._defs.items() if t == tenant_id and e == env]
        if surface_filter:
            defs = [d for d in defs if self._surface_key(d.surface) == surface_filter]
        return defs

    def upsert_corridor(self, corridor: KpiCorridor) -> KpiCorridor:
        key = (corridor.tenant_id, corridor.env, corridor.id)
        self._corridors[key] = corridor
        return corridor

    def list_corridors(self, tenant_id: str, env: str, surface: Optional[str] = None) -> List[KpiCorridor]:
        surface_filter = self._surface_key(surface)
        corridors = [c for (t, e, _), c in self._corridors.items() if t == tenant_id and e == env]
        if surface_filter:
            corridors = [c for c in corridors if self._surface_key(c.surface) == surface_filter]
        return corridors

    def get_corridor(self, tenant_id: str, env: str, corridor_id: str) -> Optional[KpiCorridor]:
        return self._corridors.get((tenant_id, env, corridor_id))

    def get_corridor_by_kpi(self, tenant_id: str, env: str, surface: Optional[str], kpi_name: str) -> Optional[KpiCorridor]:
        surface_filter = self._surface_key(surface)
        for corridor in self.list_corridors(tenant_id, env, surface=surface):
            if corridor.kpi_name == kpi_name and (surface_filter is None or self._surface_key(corridor.surface) == surface_filter):
                return corridor
        return None

    def upsert_surface_kpi_set(self, surface_set: SurfaceKpiSet) -> SurfaceKpiSet:
        key = (surface_set.tenant_id, surface_set.env, self._surface_key(surface_set.surface))
        self._surface_sets[key] = surface_set
        return surface_set

    def list_surface_kpi_sets(self, tenant_id: str, env: str, surface: Optional[str] = None) -> List[SurfaceKpiSet]:
        surface_filter = self._surface_key(surface)
        results = []
        for (t, e, surf), cfg in self._surface_sets.items():
            if t != tenant_id or e != env:
                continue
            if surface_filter and surf != surface_filter:
                continue
            results.append(cfg)
        return results

    def get_surface_kpi_set(self, tenant_id: str, env: str, surface: str) -> Optional[SurfaceKpiSet]:
        key = (tenant_id, env, self._surface_key(surface))
        return self._surface_sets.get(key)

    def record_raw_measurement(self, measurement: KpiRawMeasurement) -> KpiRawMeasurement:
        key = (measurement.tenant_id, measurement.env, self._surface_key(measurement.surface))
        self._raw.setdefault(key, []).append(measurement)
        return measurement

    def list_raw_measurements(
        self,
        tenant_id: str,
        env: str,
        surface: Optional[str] = None,
        kpi_name: Optional[str] = None,
        limit: int = 20,
    ) -> List[KpiRawMeasurement]:
        surface_filter = self._surface_key(surface)
        items: List[KpiRawMeasurement] = []
        for (t, e, surf), records in self._raw.items():
            if t != tenant_id or e != env:
                continue
            if surface_filter and surf != surface_filter:
                continue
            for record in records:
                if kpi_name and record.kpi_name != kpi_name:
                    continue
                items.append(record)
        items.sort(key=lambda r: r.created_at, reverse=True)
        return items[:limit]

    def latest_raw_measurement(self, tenant_id: str, env: str, surface: str, kpi_name: str) -> Optional[KpiRawMeasurement]:
        records = self.list_raw_measurements(tenant_id, env, surface=surface, kpi_name=kpi_name, limit=100)
        return records[0] if records else None


class FirestoreKpiRepository(InMemoryKpiRepository):
    """Placeholder for Firestore implementation."""

    def __init__(self, *args, **kwargs):  # pragma: no cover - stub
        raise NotImplementedError("FirestoreKpiRepository not implemented yet")


class FileKpiRepository(KpiRepository):
    def __init__(self, root: Optional[str] = None) -> None:
        self._root = Path(root or Path("var") / "kpi")
        self._root.mkdir(parents=True, exist_ok=True)

    def _surface_key(self, surface: Optional[str]) -> str:
        normalized = normalize_surface_id(surface)
        return normalized or "_default"

    def _scope_dir(self, tenant_id: str, env: str) -> Path:
        return self._root.joinpath(tenant_id, env)

    def _surface_dir(self, tenant_id: str, env: str, surface: Optional[str]) -> Path:
        surface_token = self._surface_key(surface)
        path = self._scope_dir(tenant_id, env) / surface_token
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _surface_dirs(self, tenant_id: str, env: str, surface: Optional[str]) -> List[Path]:
        base = self._scope_dir(tenant_id, env)
        if surface:
            dir_path = base / self._surface_key(surface)
            return [dir_path] if dir_path.exists() else []
        if not base.exists():
            return []
        return [child for child in base.iterdir() if child.is_dir()]

    def _jsonl_path(self, tenant_id: str, env: str, surface: Optional[str], name: str) -> Path:
        return self._surface_dir(tenant_id, env, surface) / name

    def _surface_kpi_file(self, tenant_id: str, env: str, surface: Optional[str]) -> Path:
        return self._surface_dir(tenant_id, env, surface) / "surface_kpis.json"

    def _raw_file(self, tenant_id: str, env: str, surface: Optional[str]) -> Path:
        return self._surface_dir(tenant_id, env, surface) / "raw.jsonl"

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

    def _write_json(self, path: Path, value: BaseModel) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fh:
            fh.write(value.model_dump_json())

    # Registry Metadata (File implementation: root encoded)
    def create_category(self, category: KpiCategory) -> KpiCategory:
        self._append_jsonl(self._scope_dir(category.tenant_id, category.env) / "categories.jsonl", category)
        return category

    def list_categories(self, tenant_id: str, env: str) -> List[KpiCategory]:
        return self._read_jsonl(self._scope_dir(tenant_id, env) / "categories.jsonl", KpiCategory)

    def create_type(self, kpi_type: KpiType) -> KpiType:
        self._append_jsonl(self._scope_dir(kpi_type.tenant_id, kpi_type.env) / "types.jsonl", kpi_type)
        return kpi_type

    def list_types(self, tenant_id: str, env: str) -> List[KpiType]:
        return self._read_jsonl(self._scope_dir(tenant_id, env) / "types.jsonl", KpiType)

    def create_definition(self, definition: KpiDefinition) -> KpiDefinition:
        self._append_jsonl(self._jsonl_path(definition.tenant_id, definition.env, definition.surface, "definitions.jsonl"), definition)
        return definition

    def list_definitions(self, tenant_id: str, env: str, surface: Optional[str] = None) -> List[KpiDefinition]:
        results: List[KpiDefinition] = []
        for surface_dir in self._surface_dirs(tenant_id, env, surface):
            results.extend(self._read_jsonl(surface_dir / "definitions.jsonl", KpiDefinition))
        return results

    def upsert_corridor(self, corridor: KpiCorridor) -> KpiCorridor:
        self._append_jsonl(self._jsonl_path(corridor.tenant_id, corridor.env, corridor.surface, "corridors.jsonl"), corridor)
        return corridor

    def list_corridors(self, tenant_id: str, env: str, surface: Optional[str] = None) -> List[KpiCorridor]:
        results: List[KpiCorridor] = []
        for surface_dir in self._surface_dirs(tenant_id, env, surface):
            results.extend(self._read_jsonl(surface_dir / "corridors.jsonl", KpiCorridor))
        return results

    def get_corridor(self, tenant_id: str, env: str, corridor_id: str) -> Optional[KpiCorridor]:
        for corridor in self.list_corridors(tenant_id, env):
            if corridor.id == corridor_id:
                return corridor
        return None

    def get_corridor_by_kpi(self, tenant_id: str, env: str, surface: Optional[str], kpi_name: str) -> Optional[KpiCorridor]:
        corridors = self.list_corridors(tenant_id, env, surface=surface)
        for corridor in corridors:
            if corridor.kpi_name == kpi_name:
                return corridor
        return None

    def upsert_surface_kpi_set(self, surface_set: SurfaceKpiSet) -> SurfaceKpiSet:
        self._write_json(self._surface_kpi_file(surface_set.tenant_id, surface_set.env, surface_set.surface), surface_set)
        return surface_set

    def list_surface_kpi_sets(self, tenant_id: str, env: str, surface: Optional[str] = None) -> List[SurfaceKpiSet]:
        results: List[SurfaceKpiSet] = []
        for surface_dir in self._surface_dirs(tenant_id, env, surface):
            path = surface_dir / "surface_kpis.json"
            if path.exists():
                results.append(SurfaceKpiSet.parse_raw(path.read_text(encoding="utf-8")))
        return results

    def get_surface_kpi_set(self, tenant_id: str, env: str, surface: str) -> Optional[SurfaceKpiSet]:
        path = self._surface_kpi_file(tenant_id, env, surface)
        if not path.exists():
            return None
        return SurfaceKpiSet.parse_raw(path.read_text(encoding="utf-8"))

    def record_raw_measurement(self, measurement: KpiRawMeasurement) -> KpiRawMeasurement:
        self._append_jsonl(self._raw_file(measurement.tenant_id, measurement.env, measurement.surface), measurement)
        return measurement

    def list_raw_measurements(
        self,
        tenant_id: str,
        env: str,
        surface: Optional[str] = None,
        kpi_name: Optional[str] = None,
        limit: int = 20,
    ) -> List[KpiRawMeasurement]:
        records: List[KpiRawMeasurement] = []
        for surface_dir in self._surface_dirs(tenant_id, env, surface):
            raw_path = surface_dir / "raw.jsonl"
            records.extend(self._read_jsonl(raw_path, KpiRawMeasurement))
        if kpi_name:
            records = [rec for rec in records if rec.kpi_name == kpi_name]
        records.sort(key=lambda rec: rec.created_at, reverse=True)
        return records[:limit]

    def latest_raw_measurement(self, tenant_id: str, env: str, surface: str, kpi_name: str) -> Optional[KpiRawMeasurement]:
        records = self.list_raw_measurements(tenant_id, env, surface=surface, kpi_name=kpi_name, limit=100)
        return records[0] if records else None
