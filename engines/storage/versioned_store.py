"""Versioned, scoped persistence helper backed by routed tabular_store."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from engines.common.identity import RequestContext
from engines.common.surface_normalizer import normalize_surface_id
from engines.storage.routing_service import TabularStoreService

logger = logging.getLogger(__name__)


@dataclass
class ScopeConfig:
    include_surface: bool = True
    include_app: bool = True
    include_user: bool = True


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class VersionedStore:
    """General-purpose versioned persistence on top of routed tabular_store."""

    def __init__(
        self,
        context: RequestContext,
        resource_kind: str,
        table_name: Optional[str] = None,
        scope_config: ScopeConfig | None = None,
    ) -> None:
        self._context = context
        self._resource_kind = resource_kind
        self._table_name = table_name or resource_kind
        self._scope_cfg = scope_config or ScopeConfig()
        self._tabular = TabularStoreService(context, resource_kind=resource_kind)

    def _scope(self, user_id: Optional[str] = None, surface_id: Optional[str] = None) -> Dict[str, Any]:
        """Build scope ensuring required identity fields are present."""
        scope: Dict[str, Any] = {
            "tenant_id": self._context.tenant_id,
            "mode": self._context.mode,
            "env": self._context.env,
            "project_id": self._context.project_id,
        }
        if not scope["project_id"]:
            raise ValueError("project_id is required for scoped persistence")
        if self._scope_cfg.include_surface:
            resolved_surface = surface_id or self._context.surface_id
            if not resolved_surface:
                raise ValueError("surface_id is required for scoped persistence")
            scope["surface_id"] = normalize_surface_id(resolved_surface)
        if self._scope_cfg.include_app:
            resolved_app = self._context.app_id
            if not resolved_app:
                raise ValueError("app_id is required for scoped persistence")
            scope["app_id"] = resolved_app
        if self._scope_cfg.include_user:
            resolved_user = user_id or self._context.user_id
            if not resolved_user:
                raise ValueError("user_id is required for scoped persistence")
            scope["user_id"] = resolved_user
        return scope

    def _base_prefix(self, scope: Dict[str, Any]) -> str:
        parts = [
            scope["tenant_id"],
            scope["mode"],
            scope.get("env") or "",
            scope["project_id"],
        ]
        if self._scope_cfg.include_surface:
            parts.append(scope.get("surface_id") or "_")
        if self._scope_cfg.include_app:
            parts.append(scope.get("app_id") or "_")
        if self._scope_cfg.include_user:
            parts.append(scope.get("user_id") or "_")
        return "#".join(parts) + "#"

    def _version_key(self, record_id: str, version: int, scope: Dict[str, Any]) -> str:
        return f"{self._base_prefix(scope)}{record_id}#v{version}"

    def _latest_key(self, record_id: str, scope: Dict[str, Any]) -> str:
        return f"{self._base_prefix(scope)}{record_id}#latest"

    def save_new(self, record_id: str, payload: Dict[str, Any], user_id: Optional[str] = None, surface_id: Optional[str] = None) -> Dict[str, Any]:
        """Create a new record at version 1."""
        scope = self._scope(user_id=user_id, surface_id=surface_id)
        now = _now_iso()
        record = {
            **payload,
            "id": record_id,
            "version": 1,
            "created_at": now,
            "updated_at": now,
            "tenant_id": scope["tenant_id"],
            "mode": scope["mode"],
            "env": scope["env"],
            "project_id": scope["project_id"],
            "surface_id": scope.get("surface_id"),
            "app_id": scope.get("app_id"),
            "user_id": scope.get("user_id"),
            "storage_key": self._version_key(record_id, 1, scope),
            "deleted": False,
        }
        self._tabular.upsert(self._table_name, record["storage_key"], record)
        self._write_latest(record_id, record, scope)
        return record

    def _write_latest(self, record_id: str, record: Dict[str, Any], scope: Dict[str, Any]) -> None:
        latest_record = {**record, "storage_key": self._latest_key(record_id, scope)}
        self._tabular.upsert(self._table_name, latest_record["storage_key"], latest_record)

    def get_latest(self, record_id: str, user_id: Optional[str] = None, surface_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        scope = self._scope(user_id=user_id, surface_id=surface_id)
        return self._tabular.get(self._table_name, self._latest_key(record_id, scope))

    def get_version(self, record_id: str, version: int, user_id: Optional[str] = None, surface_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        scope = self._scope(user_id=user_id, surface_id=surface_id)
        return self._tabular.get(self._table_name, self._version_key(record_id, version, scope))

    def list_latest(self, user_id: Optional[str] = None, surface_id: Optional[str] = None, include_deleted: bool = False) -> List[Dict[str, Any]]:
        scope = self._scope(user_id=user_id, surface_id=surface_id)
        prefix = self._base_prefix(scope)
        records = self._tabular.list_by_prefix(self._table_name, prefix)
        latest_records = [r for r in records if isinstance(r, dict) and str(r.get("storage_key", "")).endswith("latest")]
        if not include_deleted:
            latest_records = [r for r in latest_records if not r.get("deleted")]
        return latest_records

    def list_versions(self, record_id: str, user_id: Optional[str] = None, surface_id: Optional[str] = None) -> List[Dict[str, Any]]:
        scope = self._scope(user_id=user_id, surface_id=surface_id)
        prefix = f"{self._base_prefix(scope)}{record_id}#"
        records = self._tabular.list_by_prefix(self._table_name, prefix)
        return [r for r in records if r.get("storage_key") and not str(r["storage_key"]).endswith("latest")]

    def bump_version(self, record_id: str, payload: Dict[str, Any], user_id: Optional[str] = None, surface_id: Optional[str] = None, deleted: bool = False) -> Dict[str, Any]:
        scope = self._scope(user_id=user_id, surface_id=surface_id)
        latest = self.get_latest(record_id, user_id=user_id, surface_id=surface_id)
        if not latest:
            raise KeyError("record_not_found")
        new_version = int(latest.get("version", 0)) + 1
        created_at = latest.get("created_at") or _now_iso()
        now = _now_iso()
        record = {
            **latest,
            **payload,
            "id": record_id,
            "version": new_version,
            "created_at": created_at,
            "updated_at": now,
            "deleted": deleted,
            "storage_key": self._version_key(record_id, new_version, scope),
        }
        self._tabular.upsert(self._table_name, record["storage_key"], record)
        self._write_latest(record_id, record, scope)
        return record

    def delete(self, record_id: str, user_id: Optional[str] = None, surface_id: Optional[str] = None) -> Dict[str, Any]:
        """Soft-delete via versioned tombstone to preserve history."""
        return self.bump_version(record_id, payload={}, user_id=user_id, surface_id=surface_id, deleted=True)
