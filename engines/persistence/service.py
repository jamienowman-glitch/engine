"""Versioned persistence service for flow/graph/overlay artifacts (Agent B)."""
from __future__ import annotations

import logging
from typing import Dict, List, Optional
from uuid import uuid4

from engines.common.identity import RequestContext
from engines.persistence.events import emit_persistence_event
from engines.persistence.models import ArtifactCreateRequest, ArtifactRecord, ArtifactUpdateRequest
from engines.storage.versioned_store import ScopeConfig, VersionedStore

logger = logging.getLogger(__name__)


def _require_user(user_id: Optional[str]) -> str:
    if not user_id:
        raise ValueError("user_id is required for artifact persistence")
    return user_id


def _normalize_surface(context: RequestContext, requested: Optional[str]) -> str:
    resolved = requested or context.surface_id
    if not resolved:
        raise ValueError("surface_id is required for artifact persistence")
    return resolved


class ArtifactPersistenceService:
    """Shared CRUD + versioning for flow/graph/overlay definitions."""

    def __init__(self, context: RequestContext, store_name: str) -> None:
        self._context = context
        self._store_name = store_name
        self._resource = store_name.replace("_store", "")
        scope_cfg = ScopeConfig(include_surface=True, include_app=True, include_user=True)
        self._store = VersionedStore(
            context,
            resource_kind=store_name,
            table_name=store_name,
            scope_config=scope_cfg,
        )

    def create(self, req: ArtifactCreateRequest) -> ArtifactRecord:
        user_id = _require_user(self._context.user_id)
        surface_id = _normalize_surface(self._context, req.surface_id)
        record_id = req.id or uuid4().hex
        existing = self._store.get_latest(record_id, user_id=user_id, surface_id=surface_id)
        payload: Dict[str, object] = {
            "title": req.title,
            "description": req.description,
            "data": req.data,
        }
        if existing and not existing.get("deleted"):
            raise ValueError("record_exists")
        if existing and existing.get("deleted"):
            saved = self._store.bump_version(record_id, payload, user_id=user_id, surface_id=surface_id, deleted=False)
        else:
            saved = self._store.save_new(record_id, payload, user_id=user_id, surface_id=surface_id)
        emit_persistence_event(self._context, resource=self._resource, action="create", record_id=record_id, version=saved["version"])
        return ArtifactRecord(**saved)

    def update(self, record_id: str, req: ArtifactUpdateRequest) -> ArtifactRecord:
        user_id = _require_user(self._context.user_id)
        surface_id = _normalize_surface(self._context, req.surface_id)
        latest = self._store.get_latest(record_id, user_id=user_id, surface_id=surface_id)
        if not latest or latest.get("deleted"):
            raise KeyError("record_not_found")
        payload: Dict[str, object] = {}
        if req.title is not None:
            payload["title"] = req.title
        if req.description is not None:
            payload["description"] = req.description
        if req.data is not None:
            payload["data"] = req.data
        if not payload:
            payload = {}
        saved = self._store.bump_version(record_id, payload, user_id=user_id, surface_id=surface_id, deleted=False)
        emit_persistence_event(self._context, resource=self._resource, action="update", record_id=record_id, version=saved["version"])
        return ArtifactRecord(**saved)

    def delete(self, record_id: str) -> ArtifactRecord:
        user_id = _require_user(self._context.user_id)
        surface_id = _normalize_surface(self._context, None)
        latest = self._store.get_latest(record_id, user_id=user_id, surface_id=surface_id)
        if not latest:
            raise KeyError("record_not_found")
        deleted = self._store.delete(record_id, user_id=user_id, surface_id=surface_id)
        emit_persistence_event(self._context, resource=self._resource, action="delete", record_id=record_id, version=deleted["version"])
        return ArtifactRecord(**deleted)

    def get(self, record_id: str, version: Optional[int] = None, include_deleted: bool = False, surface_id: Optional[str] = None) -> ArtifactRecord:
        user_id = _require_user(self._context.user_id)
        resolved_surface = _normalize_surface(self._context, surface_id)
        record = (
            self._store.get_version(record_id, version, user_id=user_id, surface_id=resolved_surface)
            if version is not None
            else self._store.get_latest(record_id, user_id=user_id, surface_id=resolved_surface)
        )
        if not record:
            raise KeyError("record_not_found")
        if record.get("deleted") and not include_deleted:
            raise KeyError("record_not_found")
        return ArtifactRecord(**record)

    def list(self, surface_id: Optional[str] = None, include_deleted: bool = False) -> List[ArtifactRecord]:
        user_id = _require_user(self._context.user_id)
        resolved_surface = _normalize_surface(self._context, surface_id)
        records = self._store.list_latest(user_id=user_id, surface_id=resolved_surface, include_deleted=include_deleted)
        return [ArtifactRecord(**r) for r in records]

    def history(self, record_id: str, surface_id: Optional[str] = None) -> List[ArtifactRecord]:
        user_id = _require_user(self._context.user_id)
        resolved_surface = _normalize_surface(self._context, surface_id)
        records = self._store.list_versions(record_id, user_id=user_id, surface_id=resolved_surface)
        sorted_records = sorted(records, key=lambda r: r.get("version", 0))
        return [ArtifactRecord(**r) for r in sorted_records]
