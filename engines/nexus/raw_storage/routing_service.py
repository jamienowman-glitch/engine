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


class S3ObjectStoreAdapter:
    """Adapter wrapping S3RawStorageRepository to match ObjectStoreAdapter protocol.
    
    Converts S3RawStorageRepository (presigned POST focused) to ObjectStoreAdapter interface
    (direct PUT/GET focused) for routing-based backend selection.
    """
    
    def __init__(self, s3_repo, ctx: RequestContext):
        """Initialize with S3 repository and request context for tenant/env."""
        self.s3_repo = s3_repo
        self.ctx = ctx
    
    def put_object(
        self, 
        key: str, 
        content: bytes, 
        context: RequestContext,
    ) -> str:
        """Store a blob to S3 and return its URI."""
        return self.s3_repo.put_object(
            key=key,
            content=content,
            tenant_id=context.tenant_id,
            env=context.env
        )
    
    def get_object(
        self, 
        key: str, 
        context: RequestContext,
    ) -> Optional[bytes]:
        """Retrieve a blob from S3."""
        return self.s3_repo.get_object(
            key=key,
            tenant_id=context.tenant_id,
            env=context.env
        )
    
    def delete_object(
        self, 
        key: str, 
        context: RequestContext,
    ) -> None:
        """Delete a blob from S3 (not yet implemented)."""
        # S3 delete_object not yet implemented in S3RawStorageRepository
        # Fail-fast for now; can be added as needed
        raise NotImplementedError("S3 delete_object not yet implemented for Lane 4")
    
    def list_objects(
        self, 
        prefix: str,
        context: RequestContext,
    ) -> list[str]:
        """List blob keys in S3 (not yet implemented)."""
        # S3 list_objects not yet implemented in S3RawStorageRepository
        raise NotImplementedError("S3 list_objects not yet implemented for Lane 4")
    
    # Compatibility methods for RawStorageService interface
    
    def generate_presigned_post(
        self, tenant_id: str, env: str, asset_id: str, filename: str, content_type: str
    ) -> Tuple[str, Dict[str, str]]:
        """Generate presigned POST URL for client-side upload."""
        return self.s3_repo.generate_presigned_post(
            tenant_id=tenant_id,
            env=env,
            asset_id=asset_id,
            filename=filename,
            content_type=content_type
        )
    
    def get_uri(self, tenant_id: str, env: str, asset_id: str, filename: str) -> str:
        """Construct S3 URI for asset."""
        return self.s3_repo.get_uri(tenant_id, env, asset_id, filename)


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
                # Wrap S3RawStorageRepository to match ObjectStoreAdapter protocol
                from engines.nexus.raw_storage.repository import S3RawStorageRepository
                bucket = route.config.get("bucket") if route.config else None
                s3_repo = S3RawStorageRepository(bucket_name=bucket)
                return S3ObjectStoreAdapter(s3_repo, ctx)
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

