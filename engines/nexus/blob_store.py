"""Nexus Blob Store wrapper using fsspec (E-04)."""
import fsspec
import os
from typing import Optional, Union

from engines.nexus.schemas import SpaceKey

class NexusBlobStore:
    """
    Blob storage wrapper using fsspec.
    Handles media storage with routing via SpaceKey.
    """

    def __init__(self, protocol: str = "file", root_path: str = "/tmp/nexus_media", **storage_options):
        self.protocol = protocol
        self.root_path = root_path.rstrip("/")
        self.fs = fsspec.filesystem(protocol, **storage_options)

        # Ensure root exists for local
        if protocol == "file" and not os.path.exists(self.root_path):
            os.makedirs(self.root_path, exist_ok=True)

    def _get_path(self, space_key: SpaceKey, blob_id: str) -> str:
        """
        Constructs path: {root}/{tenant_id}/{env}/{project_id}/{surface_id}/{blob_id}
        """
        path = (
            f"{self.root_path}/"
            f"{space_key.tenant_id}/"
            f"{space_key.env}/"
            f"{space_key.project_id}/"
            f"{space_key.surface_id}/"
            f"{blob_id}"
        )
        return path

    def put_bytes(self, space_key: SpaceKey, blob_id: str, data: bytes) -> str:
        """
        Write bytes to storage. Returns the URI.
        """
        path = self._get_path(space_key, blob_id)

        # Ensure parent directory exists for local
        if self.protocol == "file":
            os.makedirs(os.path.dirname(path), exist_ok=True)

        with self.fs.open(path, "wb") as f:
            f.write(data)

        return self.resolve_uri(space_key, blob_id)

    def get_bytes(self, space_key: SpaceKey, blob_id: str) -> bytes:
        """
        Read bytes from storage.
        """
        path = self._get_path(space_key, blob_id)
        if not self.fs.exists(path):
            raise FileNotFoundError(f"Blob not found: {path}")

        with self.fs.open(path, "rb") as f:
            return f.read()

    def exists(self, space_key: SpaceKey, blob_id: str) -> bool:
        """Check if blob exists."""
        path = self._get_path(space_key, blob_id)
        return self.fs.exists(path)

    def resolve_uri(self, space_key: SpaceKey, blob_id: str) -> str:
        """Return the fully qualified URI."""
        path = self._get_path(space_key, blob_id)
        if self.protocol == "file":
            return path
        return f"{self.protocol}://{path}"
