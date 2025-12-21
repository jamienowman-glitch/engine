"""Raw Storage service layer."""
from __future__ import annotations

import uuid
from typing import Any, Dict

from engines.common.identity import RequestContext
from engines.logging.event_log import EventLogEntry, default_event_logger
from engines.nexus.raw_storage.models import RawAsset
from engines.nexus.raw_storage.repository import RawStorageRepository, S3RawStorageRepository


class RawStorageService:
    def __init__(self, repo: RawStorageRepository | None = None):
        self.repo = repo or S3RawStorageRepository()

    def presign_upload(
        self, ctx: RequestContext, filename: str, content_type: str
    ) -> Dict[str, Any]:
        """
        Generate a presigned upload URL for a new asset.
        Emits 'raw_asset_presigned' event.
        """
        asset_id = str(uuid.uuid4())
        
        url, fields = self.repo.generate_presigned_post(
            tenant_id=ctx.tenant_id,
            env=ctx.env,
            asset_id=asset_id,
            filename=filename,
            content_type=content_type
        )
        
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
        (Note: Does not verify S3 existence here to keep it fast, but could in future).
        Emits 'raw_asset_registered' event.
        """
        if metadata is None:
            metadata = {}

        # Construct URI from repo logic (single source of truth for path)
        # S3RawStorageRepository specific but standard Protocol doesn't have get_uri
        # We assume usage of S3RawStorageRepository or compatible behavior
        if isinstance(self.repo, S3RawStorageRepository):
            uri = self.repo.get_uri(ctx.tenant_id, ctx.env, asset_id, filename)
        else:
            uri = f"urn:northstar:raw:{ctx.tenant_id}:{asset_id}"

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
        self.repo.persist_metadata(asset)

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
