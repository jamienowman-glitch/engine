"""Object store service with routing-based backend resolution (Lane 3 wiring).

Routes object_store resource_kind through routing registry to appropriate adapter:
- filesystem (default for dev, requires routing entry)
- s3 (requires AWS credentials + routing entry)

Maintains compatibility with existing RawStorageService interface for presigning/registration.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, Optional, Tuple

from engines.common.identity import RequestContext
from engines.logging.event_log import EventLogEntry, default_event_logger
from engines.nexus.raw_storage.filesystem_adapter import FileSystemObjectStore
from engines.nexus.raw_storage.models import RawAsset
from engines.routing.registry import MissingRoutingConfig, routing_registry

logger = logging.getLogger(__name__)


class ObjectStoreService:
    """Resolves and uses object storage via routing registry.
    
    Provides unified interface compatible with RawStorageService:
    - presign_upload() for S3 presigned URLs
    - register_asset() for metadata persistence
    
    Also provides low-level methods:
    - put(key, content, ctx) for direct storage
    - get(key, ctx) for retrieval
    - delete(key, ctx) for deletion
    """
    
    def _resolve_adapter_for_context(self, ctx: RequestContext):
        """Resolve object_store backend via routing registry (no env selection)."""
        try:
            registry = routing_registry()
            route = registry.get_route(
                resource_kind="object_store",
                tenant_id=ctx.tenant_id,
                env=ctx.env,
                project_id=ctx.project_id,
            )
            
            if not route:
                raise MissingRoutingConfig(
                    f"No route configured for object_store in {ctx.tenant_id}/{ctx.env}. "
                    f"Configure via /routing/routes with backend_type=filesystem or s3."
                )
            
            backend_type = (route.backend_type or "").lower()
            
            if backend_type == "filesystem":
                return FileSystemObjectStore()
            elif backend_type == "s3":
                # Import S3 adapter if available; for now, use S3RawStorageRepository
                from engines.nexus.raw_storage.repository import S3RawStorageRepository
                bucket = route.config.get("bucket")
                return S3RawStorageRepository(bucket_name=bucket)
            else:
                raise RuntimeError(
                    f"Unsupported object_store backend_type='{backend_type}'. "
                    f"Use 'filesystem' or 's3'."
                )
        except MissingRoutingConfig as e:
            raise RuntimeError(str(e)) from e
    
    # RawStorageService-compatible interface for presigning
    
    def presign_upload(
        self, ctx: RequestContext, filename: str, content_type: str
    ) -> Dict[str, Any]:
        """
        Generate a presigned upload URL for a new asset.
        For S3 backends: returns presigned POST fields.
        For filesystem: returns filesystem put endpoint info.
        """
        adapter = self._resolve_adapter_for_context(ctx)
        asset_id = str(uuid.uuid4())
        
        # For S3 adapters, they have generate_presigned_post
        if hasattr(adapter, 'generate_presigned_post'):
            url, fields = adapter.generate_presigned_post(
                tenant_id=ctx.tenant_id,
                env=ctx.env,
                asset_id=asset_id,
                filename=filename,
                content_type=content_type
            )
        else:
            # For filesystem, generate a local endpoint URL
            url = f"/nexus/raw/fs-put/{asset_id}/{filename}"
            fields = {"asset_id": asset_id, "filename": filename}
        
        # Log intent
        default_event_logger(
            EventLogEntry(
                event_type="raw_asset_presigned",
                asset_type="raw_asset",
                asset_id=asset_id,
                tenant_id=ctx.tenant_id,
                user_id=ctx.user_id,
                request_id=ctx.request_id,
                trace_id=ctx.request_id,
                metadata={
                    "filename": filename,
                    "content_type": content_type,
                    "env": ctx.env,
                },
            )
        )
        
        return {
            "asset_id": asset_id,
            "url": url,
            "fields": fields,
            "filename": filename
        }
    
    def register_asset(
        self,
        ctx: RequestContext,
        asset_id: str,
        filename: str,
        content_type: str,
        size_bytes: int | None = None,
        metadata: Dict[str, Any] | None = None,
    ) -> RawAsset:
        """
        Register a completed upload as a RawAsset.
        Persists metadata via routing-resolved adapter.
        """
        if metadata is None:
            metadata = {}
        
        adapter = self._resolve_adapter_for_context(ctx)
        
        # Construct URI based on backend type
        if hasattr(adapter, 'get_uri'):
            # S3RawStorageRepository has get_uri
            uri = adapter.get_uri(ctx.tenant_id, ctx.env, asset_id, filename)
        else:
            # Filesystem or other adapters
            uri = f"urn:northstar:object_store:{ctx.tenant_id}:{asset_id}:{filename}"
        
        asset = RawAsset(
            asset_id=asset_id,
            tenant_id=ctx.tenant_id,
            env=ctx.env,
            uri=uri,
            filename=filename,
            size_bytes=size_bytes,
            content_type=content_type,
            metadata=metadata,
            created_by=ctx.user_id
        )
        
        # Persist metadata if adapter supports it
        if hasattr(adapter, 'persist_metadata'):
            adapter.persist_metadata(asset)
        
        # Log registration
        default_event_logger(
            EventLogEntry(
                event_type="raw_asset_registered",
                asset_type="raw_asset",
                asset_id=asset_id,
                tenant_id=ctx.tenant_id,
                user_id=ctx.user_id,
                request_id=ctx.request_id,
                trace_id=ctx.request_id,
                metadata={
                    "uri": uri,
                    "filename": filename,
                    "size_bytes": size_bytes,
                    "content_type": content_type,
                },
            )
        )
        
        return asset
    
    # Low-level object store interface
    
    def put(
        self, 
        ctx: RequestContext,
        key: str, 
        content: bytes,
    ) -> str:
        """Store a blob and return URI/reference."""
        adapter = self._resolve_adapter_for_context(ctx)
        return adapter.put_object(key, content, ctx)
    
    def get(self, ctx: RequestContext, key: str) -> Optional[bytes]:
        """Retrieve a blob by key."""
        adapter = self._resolve_adapter_for_context(ctx)
        return adapter.get_object(key, ctx)
    
    def delete(self, ctx: RequestContext, key: str) -> None:
        """Delete a blob by key."""
        adapter = self._resolve_adapter_for_context(ctx)
        adapter.delete_object(key, ctx)
    
    def list(self, ctx: RequestContext, prefix: str) -> list[str]:
        """List blob keys matching prefix."""
        adapter = self._resolve_adapter_for_context(ctx)
        return adapter.list_objects(prefix, ctx)

