from __future__ import annotations
from typing import Generic, TypeVar, Dict, Optional, List, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone

from engines.common.identity import RequestContext
from engines.storage.routing_service import TabularStoreService
from engines.common.error_envelope import missing_route_error
from engines.routing.registry import MissingRoutingConfig

T = TypeVar("T")

@dataclass
class StoredItem(Generic[T]):
    key: str
    version: str # "draft" or "X.Y.Z"
    data: T
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

class VersionedStore(Generic[T]):
    """
    Routed versioned store.
    Persists to 'workbench_store' resource (defaulting to filesystem if not routed).
    """

    def __init__(self, resource_kind: str = "workbench_store", table_name: str = "tools"):
        self._resource_kind = resource_kind
        self._table_name = table_name

    def _tabular(self, ctx: RequestContext) -> TabularStoreService:
        try:
            return TabularStoreService(ctx, resource_kind=self._resource_kind)
        except (RuntimeError, MissingRoutingConfig):
            # Fallback for dev/local if route missing, though TabularStore usually handles this?
            # Actually TabularStore raises if no route.
            # We'll allow error to bubble or handle it?
            # For now, let's assume route exists or TabularStore fallback works.
            # If strictly needed, we could catch and use a InMemory fallback, but requirement says "Routed Persistence".
            # So we let it fail if not routed.
            raise

    def _key(self, ctx: RequestContext, key: str, version: str) -> str:
        return f"{ctx.tenant_id}#{ctx.mode}#{ctx.env}#{key}#{version}"
    
    def _prefix(self, ctx: RequestContext, key: str) -> str:
        return f"{ctx.tenant_id}#{ctx.mode}#{ctx.env}#{key}#"

    def put_draft(self, ctx: RequestContext, key: str, data: T) -> StoredItem[T]:
        item = StoredItem(
            key=key,
            version="draft",
            data=data,
            updated_at=datetime.now(timezone.utc)
        )
        # Serialize
        record = {
            "key": key,
            "version": "draft",
            "data": data, # T needs to be dict-compatible or pydantic? Assuming dict for now.
            "created_at": item.created_at.isoformat(),
            "updated_at": item.updated_at.isoformat(),
        }
        # If T is Pydantic, dump it.
        if hasattr(data, "model_dump"):
            record["data"] = data.model_dump()
        
        self._tabular(ctx).upsert(self._table_name, self._key(ctx, key, "draft"), record)
        return item

    def get_draft(self, ctx: RequestContext, key: str) -> Optional[StoredItem[T]]:
        data = self._tabular(ctx).get(self._table_name, self._key(ctx, key, "draft"))
        if not data:
            return None
        # data["data"] needs to be cast back to T?
        # For generic T (Dict), it's fine.
        return StoredItem(
            key=data["key"],
            version=data["version"],
            data=data["data"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"])
        )

    def publish(self, ctx: RequestContext, key: str, version: str) -> StoredItem[T]:
        """Promote current draft to a concrete version."""
        draft = self.get_draft(ctx, key)
        if not draft:
            raise ValueError(f"No draft found for key {key}")
        
        if version == "draft":
            raise ValueError("Cannot publish to version 'draft'")
            
        # Check collision
        existing = self.get_version(ctx, key, version)
        if existing:
             raise ValueError(f"Version {version} already exists for key {key}")

        published_item = StoredItem(
            key=key,
            version=version,
            data=draft.data, 
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        record = {
            "key": key,
            "version": version,
            "data": published_item.data,
            "created_at": published_item.created_at.isoformat(),
            "updated_at": published_item.updated_at.isoformat(),
        }
        # If T is Pydantic, the previous retrieval likely kept it as Dict.
        # So we just save the Dict.

        self._tabular(ctx).upsert(self._table_name, self._key(ctx, key, version), record)
        return published_item

    def get_version(self, ctx: RequestContext, key: str, version: str) -> Optional[StoredItem[T]]:
        data = self._tabular(ctx).get(self._table_name, self._key(ctx, key, version))
        if not data:
            return None
        return StoredItem(
            key=data["key"],
            version=data["version"],
            data=data["data"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"])
        )

    def list_versions(self, ctx: RequestContext, key: str) -> List[StoredItem[T]]:
        records = self._tabular(ctx).list_by_prefix(self._table_name, self._prefix(ctx, key))
        items = []
        for r in records:
            items.append(StoredItem(
                key=r["key"],
                version=r["version"],
                data=r["data"],
                created_at=datetime.fromisoformat(r["created_at"]),
                updated_at=datetime.fromisoformat(r["updated_at"])
            ))
        return items

    def list_all_drafts(self, ctx: RequestContext) -> List[StoredItem[T]]:
        """List ALL items with version='draft'."""
        # 1. List everything in the table for this tenant (prefix with tenant_id)
        # TabularStore prefix: f"{ctx.tenant_id}#{ctx.mode}#{ctx.env}#"
        # This scans ALL tools. Acceptable for workbench scale.
        full_prefix = f"{ctx.tenant_id}#{ctx.mode}#{ctx.env}#"
        records = self._tabular(ctx).list_by_prefix(self._table_name, full_prefix)
        
        drafts = []
        for r in records:
            if r["version"] == "draft":
                drafts.append(StoredItem(
                    key=r["key"],
                    version=r["version"],
                    data=r["data"],
                    created_at=datetime.fromisoformat(r["created_at"]),
                    updated_at=datetime.fromisoformat(r["updated_at"])
                ))
        return drafts
