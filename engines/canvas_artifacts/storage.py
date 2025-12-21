from __future__ import annotations

import asyncio
from typing import Protocol, Optional
from abc import abstractmethod

class ArtifactStorage(Protocol):
    async def upload(self, key: str, data: bytes, mime_type: str) -> str:
        """Upload data and return public/presigned URL."""
        ...
        
    async def get_url(self, key: str) -> Optional[str]:
        """Get access URL for key."""
        ...

class InMemoryArtifactStorage:
    def __init__(self):
        self._store: dict[str, tuple[bytes, str]] = {} # key -> (data, mime)
        self._base_url = "http://localhost/artifacts"

    async def upload(self, key: str, data: bytes, mime_type: str) -> str:
        self._store[key] = (data, mime_type)
        return f"{self._base_url}/{key}"

    async def get_url(self, key: str) -> Optional[str]:
        if key in self._store:
            return f"{self._base_url}/{key}"
        return None

# Singleton stub for Phase 04
artifact_storage = InMemoryArtifactStorage()
