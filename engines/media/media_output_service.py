"""Media Output Store (Builder C).

Reuses object_store backend for blob storage + persists metadata separately.
Metadata: mime, size, checksum, object_ref (URI).
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from engines.common.identity import RequestContext
from engines.nexus.raw_storage.routing_service import ObjectStoreService
from engines.storage.routing_service import TabularStoreService

logger = logging.getLogger(__name__)


class MediaOutputMetadata:
    """Metadata for media output: mime, size, checksum, object_ref."""
    
    def __init__(
        self,
        media_id: str,
        object_ref: str,
        mime_type: str,
        size_bytes: int,
        checksum_sha256: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.media_id = media_id
        self.object_ref = object_ref  # s3://bucket/path, azure-blob://container/path, gs://bucket/path
        self.mime_type = mime_type
        self.size_bytes = size_bytes
        self.checksum_sha256 = checksum_sha256
        self.user_id = user_id
        self.session_id = session_id
        self.metadata = metadata or {}
        self.created_at = datetime.now(timezone.utc).isoformat()
    
    def dict(self) -> Dict[str, Any]:
        return {
            "media_id": self.media_id,
            "object_ref": self.object_ref,
            "mime_type": self.mime_type,
            "size_bytes": self.size_bytes,
            "checksum_sha256": self.checksum_sha256,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> MediaOutputMetadata:
        return MediaOutputMetadata(
            media_id=data["media_id"],
            object_ref=data["object_ref"],
            mime_type=data["mime_type"],
            size_bytes=data["size_bytes"],
            checksum_sha256=data["checksum_sha256"],
            user_id=data.get("user_id"),
            session_id=data.get("session_id"),
            metadata=data.get("metadata", {}),
        )


class MediaOutputService:
    """Manage media output: store blobs + metadata."""
    
    def __init__(self, context: RequestContext) -> None:
        self._context = context
        self._object_store = ObjectStoreService()
        self._tabular_service = TabularStoreService(context)
    
    def store_media(
        self,
        media_id: str,
        content: bytes,
        mime_type: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MediaOutputMetadata:
        """Store media content and persist metadata.
        
        Args:
            media_id: Unique media identifier
            content: Blob content (bytes)
            mime_type: MIME type (e.g., "image/png", "video/mp4", "application/json")
            user_id: Optional user who created media
            session_id: Optional session where media was created
            metadata: Optional additional metadata dict
        
        Returns:
            MediaOutputMetadata with object_ref (URI) and checksum
        """
        try:
            # Compute checksum
            checksum_sha256 = hashlib.sha256(content).hexdigest()
            
            # Store blob (routing will select backend: s3, azure_blob, gcs)
            object_key = f"media/{media_id}"
            object_ref = self._object_store.put(object_key, content, self._context)
            
            # Create metadata
            media_metadata = MediaOutputMetadata(
                media_id=media_id,
                object_ref=object_ref,
                mime_type=mime_type,
                size_bytes=len(content),
                checksum_sha256=checksum_sha256,
                user_id=user_id,
                session_id=session_id,
                metadata=metadata,
            )
            
            # Persist metadata to tabular store
            self._tabular_service.upsert(
                "media_output_metadata",
                f"media#{media_id}",
                media_metadata.dict(),
            )
            
            logger.info("Stored media: %s (size=%d bytes, mime=%s)", media_id, len(content), mime_type)
            return media_metadata
        except Exception as exc:
            logger.error("Failed to store media: %s", exc)
            raise
    
    def get_media_metadata(self, media_id: str) -> Optional[MediaOutputMetadata]:
        """Fetch media metadata."""
        try:
            data = self._tabular_service.get("media_output_metadata", f"media#{media_id}")
            if data:
                return MediaOutputMetadata.from_dict(data)
        except Exception as exc:
            logger.warning("Failed to get media metadata: %s", exc)
        return None
    
    def get_media(self, media_id: str) -> Optional[bytes]:
        """Retrieve media blob by ID."""
        try:
            metadata = self.get_media_metadata(media_id)
            if not metadata:
                return None
            
            # Extract key from object_ref (e.g., s3://bucket/media/id → media/id)
            # This is simplistic; real impl would parse URIs properly
            object_key = f"media/{media_id}"
            return self._object_store.get(object_key, self._context)
        except Exception as exc:
            logger.warning("Failed to get media: %s", exc)
        return None
    
    def delete_media(self, media_id: str) -> None:
        """Delete media blob and metadata."""
        try:
            # Delete blob
            object_key = f"media/{media_id}"
            self._object_store.delete(object_key, self._context)
            
            # Delete metadata
            self._tabular_service.delete("media_output_metadata", f"media#{media_id}")
            
            logger.info("Deleted media: %s", media_id)
        except Exception as exc:
            logger.error("Failed to delete media: %s", exc)
            raise
    
    def list_media_for_session(self, session_id: str) -> list[MediaOutputMetadata]:
        """List all media for a session."""
        records = []
        try:
            # Query by session_id (requires tabular store support)
            # Simple impl: list all and filter
            all_records = self._tabular_service.list_by_prefix("media_output_metadata", "media#")
            for record in all_records:
                try:
                    metadata = MediaOutputMetadata.from_dict(record)
                    if metadata.session_id == session_id:
                        records.append(metadata)
                except Exception as exc:
                    logger.warning("Failed to deserialize media metadata: %s", exc)
        except Exception as exc:
            logger.warning("Failed to list session media: %s", exc)
        return records
