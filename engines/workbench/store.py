from __future__ import annotations
from typing import Generic, TypeVar, Dict, Optional, List, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone

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
    In-memory versioned store (for now, backed by dict).
    Supports:
    - put_draft(key, data) -> overwrites existing draft
    - get_draft(key)
    - publish(key, version) -> promotes draft to version (immutable)
    - get_version(key, version)
    - list_versions(key)
    """

    def __init__(self):
        # Map: key -> version -> StoredItem
        self._storage: Dict[str, Dict[str, StoredItem[T]]] = {}

    def put_draft(self, key: str, data: T) -> StoredItem[T]:
        if key not in self._storage:
            self._storage[key] = {}
        
        item = StoredItem(
            key=key,
            version="draft",
            data=data,
            updated_at=datetime.now(timezone.utc)
        )
        self._storage[key]["draft"] = item
        return item

    def get_draft(self, key: str) -> Optional[StoredItem[T]]:
        versions = self._storage.get(key)
        if not versions:
            return None
        return versions.get("draft")

    def publish(self, key: str, version: str) -> StoredItem[T]:
        """Promote current draft to a concrete version."""
        draft = self.get_draft(key)
        if not draft:
            raise ValueError(f"No draft found for key {key}")
        
        if version == "draft":
            raise ValueError("Cannot publish to version 'draft'")
            
        versions = self._storage[key]
        if version in versions:
             raise ValueError(f"Version {version} already exists for key {key}")

        published_item = StoredItem(
            key=key,
            version=version,
            data=draft.data, # Deep copy recommended in real impl
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        versions[version] = published_item
        return published_item

    def get_version(self, key: str, version: str) -> Optional[StoredItem[T]]:
        versions = self._storage.get(key)
        if not versions:
            return None
        return versions.get(version)

    def list_versions(self, key: str) -> List[StoredItem[T]]:
        versions = self._storage.get(key)
        if not versions:
            return []
        # Sort drafts first? Or explicit semantic sort?
        # For now, just return all.
        return list(versions.values())
