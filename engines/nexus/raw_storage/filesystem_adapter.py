"""Filesystem-backed raw storage adapter for object_store resource_kind (Lane 2 adapter).

Provides durable blob storage using filesystem.
Location: var/object_store/{tenant_id}/{env}/{surface_id or "_"}/blobs/
"""
from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Dict, Optional, Protocol, Tuple

from engines.common.identity import RequestContext
from engines.common.surface_normalizer import normalize_surface_id

logger = logging.getLogger(__name__)


class ObjectStoreAdapter(Protocol):
    """Abstraction for object storage (PUT/GET/DELETE blobs)."""
    
    def put_object(
        self, 
        key: str, 
        content: bytes, 
        context: RequestContext,
    ) -> str:
        """Store a blob and return a storage URI/reference."""
        ...
    
    def get_object(
        self, 
        key: str, 
        context: RequestContext,
    ) -> Optional[bytes]:
        """Retrieve a blob by key; return None if not found."""
        ...
    
    def delete_object(
        self, 
        key: str, 
        context: RequestContext,
    ) -> None:
        """Delete a blob by key (no-op if not found)."""
        ...
    
    def list_objects(
        self, 
        prefix: str,
        context: RequestContext,
    ) -> list[str]:
        """List keys matching prefix."""
        ...


class FileSystemObjectStore:
    """Filesystem-backed object store using simple directory hierarchy.
    
    Path structure:
      var/object_store/{tenant_id}/{env}/{surface_id or "_"}/blobs/{key}
    
    Key format: arbitrary string, but should avoid slashes (will be stored as single file).
    """
    
    def __init__(self, base_dir: Optional[str | Path] = None) -> None:
        self._base_dir = Path(base_dir or Path.cwd() / "var" / "object_store")
        self._base_dir.mkdir(parents=True, exist_ok=True)
    
    def _blob_dir(self, context: RequestContext) -> Path:
        """Deterministic directory path for blobs."""
        surface = normalize_surface_id(context.surface_id) if context.surface_id else "_"
        env = (context.env or "dev").lower()
        tenant = context.tenant_id
        
        return self._base_dir / tenant / env / surface / "blobs"
    
    def _blob_path(self, key: str, context: RequestContext) -> Path:
        """Full path to a blob file.
        
        Sanitize key to prevent directory traversal.
        """
        safe_key = key.replace("/", "_").replace("..", "_").replace("~", "_")
        return self._blob_dir(context) / safe_key
    
    def put_object(
        self, 
        key: str, 
        content: bytes, 
        context: RequestContext,
    ) -> str:
        """Store a blob and return a reference URI.
        
        Enforces backend-class guard: filesystem backend forbidden in sellable modes.
        """
        # Backend-class guard (Lane 2): forbid filesystem in sellable modes
        from engines.routing.manager import ForbiddenBackendClass, SELLABLE_MODES
        mode_lower = (context.mode or "lab").lower()
        if mode_lower in SELLABLE_MODES:
            raise ForbiddenBackendClass(
                f"[FORBIDDEN_BACKEND_CLASS] Backend 'filesystem' is forbidden in mode '{context.mode}' "
                f"(resource_kind=object_store, tenant={context.tenant_id}, env={context.env}). "
                f"Sellable modes require cloud backends. Use 'lab' mode for filesystem."
            )
        
        blob_dir = self._blob_dir(context)
        blob_dir.mkdir(parents=True, exist_ok=True)
        
        blob_path = self._blob_path(key, context)
        
        try:
            with open(blob_path, "wb") as f:
                f.write(content)
            
            # Return a reference URI
            relative = blob_path.relative_to(self._base_dir)
            return f"fs://{self._base_dir.name}/{relative}"
        except Exception as exc:
            logger.error(f"Failed to store blob {key}: {exc}")
            raise RuntimeError(f"Object store PUT failed: {exc}") from exc
    
    def get_object(
        self, 
        key: str, 
        context: RequestContext,
    ) -> Optional[bytes]:
        """Retrieve a blob by key.
        
        Enforces backend-class guard: filesystem backend forbidden in sellable modes.
        """
        # Backend-class guard (Lane 2): forbid filesystem in sellable modes
        from engines.routing.manager import ForbiddenBackendClass, SELLABLE_MODES
        mode_lower = (context.mode or "lab").lower()
        if mode_lower in SELLABLE_MODES:
            raise ForbiddenBackendClass(
                f"[FORBIDDEN_BACKEND_CLASS] Backend 'filesystem' is forbidden in mode '{context.mode}' "
                f"(resource_kind=object_store, tenant={context.tenant_id}, env={context.env}). "
                f"Sellable modes require cloud backends. Use 'lab' mode for filesystem."
            )
        
        blob_path = self._blob_path(key, context)
        
        if not blob_path.exists():
            return None
        
        try:
            with open(blob_path, "rb") as f:
                return f.read()
        except Exception as exc:
            logger.error(f"Failed to retrieve blob {key}: {exc}")
            return None
    
    def delete_object(
        self, 
        key: str, 
        context: RequestContext,
    ) -> None:
        """Delete a blob by key (no-op if not found)."""
        blob_path = self._blob_path(key, context)
        
        if blob_path.exists():
            try:
                blob_path.unlink()
            except Exception as exc:
                logger.warning(f"Failed to delete blob {key}: {exc}")
    
    def list_objects(
        self, 
        prefix: str,
        context: RequestContext,
    ) -> list[str]:
        """List blob keys matching prefix."""
        blob_dir = self._blob_dir(context)
        
        if not blob_dir.exists():
            return []
        
        results = []
        for blob_file in blob_dir.iterdir():
            if blob_file.is_file() and blob_file.name.startswith(prefix):
                results.append(blob_file.name)
        
        return sorted(results)
