"""Object Store cloud adapters: Azure Blob, GCS.

Builder C: Tenant/project namespacing, put/get round-trip with headers.
S3 adapter exists from Lane 4. This adds Blob and GCS.
resource_kind=object_store.
"""
from __future__ import annotations

import logging
from typing import Optional, Protocol

try:  # pragma: no cover
    from azure.storage.blob import BlobServiceClient  # type: ignore
except Exception:  # pragma: no cover
    BlobServiceClient = None

try:  # pragma: no cover
    from google.cloud import storage  # type: ignore
except Exception:  # pragma: no cover
    storage = None

logger = logging.getLogger(__name__)


class ObjectStoreAdapter(Protocol):
    """Protocol for object store adapters."""
    
    def put_object(self, key: str, content: bytes, tenant_id: str, env: str) -> str:
        """Store object, return URI."""
        ...
    
    def get_object(self, key: str, tenant_id: str, env: str) -> Optional[bytes]:
        """Retrieve object, return bytes or None."""
        ...
    
    def delete_object(self, key: str, tenant_id: str, env: str) -> None:
        """Delete object."""
        ...
    
    def list_objects(self, prefix: str, tenant_id: str, env: str) -> list[str]:
        """List object keys with prefix."""
        ...
    
    def generate_presigned_post(self, key: str, tenant_id: str, env: str) -> dict:
        """Generate presigned POST for client uploads."""
        ...


class AzureBlobStorageAdapter:
    """Azure Blob Storage adapter."""
    
    def __init__(
        self,
        connection_string: Optional[str] = None,
        container: str = "raw-objects",
    ) -> None:
        if BlobServiceClient is None:
            raise RuntimeError("azure-storage-blob is required for Azure Blob Storage")
        
        self._connection_string = connection_string
        self._container = container
        
        if not self._connection_string:
            import os
            self._connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        
        if not self._connection_string:
            raise RuntimeError("AZURE_STORAGE_CONNECTION_STRING required for Blob Storage")
        
        try:
            self._client = BlobServiceClient.from_connection_string(self._connection_string)
            self._container_client = self._client.get_container_client(self._container)
        except Exception as exc:
            raise RuntimeError(f"Failed to initialize Blob Storage: {exc}") from exc
    
    def put_object(self, key: str, content: bytes, tenant_id: str, env: str) -> str:
        """Store blob with tenant/env namespacing."""
        try:
            # Namespace: tenants/{tenant}/{env}/raw/{key}
            blob_key = f"tenants/{tenant_id}/{env}/raw/{key}"
            blob_client = self._container_client.get_blob_client(blob_key)
            blob_client.upload_blob(content, overwrite=True)
            
            # Return URI
            uri = f"azure-blob://{self._container}/{blob_key}"
            logger.info("Stored blob: %s", uri)
            return uri
        except Exception as exc:
            logger.error("Failed to store blob: %s", exc)
            raise RuntimeError(f"Failed to store object: {exc}") from exc
    
    def get_object(self, key: str, tenant_id: str, env: str) -> Optional[bytes]:
        """Retrieve blob."""
        try:
            blob_key = f"tenants/{tenant_id}/{env}/raw/{key}"
            blob_client = self._container_client.get_blob_client(blob_key)
            return blob_client.download_blob().readall()
        except Exception as exc:
            logger.warning("Failed to retrieve blob: %s", exc)
        return None
    
    def delete_object(self, key: str, tenant_id: str, env: str) -> None:
        """Delete blob."""
        try:
            blob_key = f"tenants/{tenant_id}/{env}/raw/{key}"
            blob_client = self._container_client.get_blob_client(blob_key)
            blob_client.delete_blob()
        except Exception as exc:
            logger.error("Failed to delete blob: %s", exc)
            raise RuntimeError(f"Failed to delete object: {exc}") from exc
    
    def list_objects(self, prefix: str, tenant_id: str, env: str) -> list[str]:
        """List blobs with prefix."""
        keys = []
        try:
            prefix_filter = f"tenants/{tenant_id}/{env}/raw/{prefix}"
            for blob in self._container_client.list_blobs(name_starts_with=prefix_filter):
                keys.append(blob.name)
        except Exception as exc:
            logger.warning("Failed to list blobs: %s", exc)
        return keys
    
    def generate_presigned_post(self, key: str, tenant_id: str, env: str) -> dict:
        """Generate presigned POST for client uploads (not native in Blob Storage)."""
        # Blob Storage doesn't have presigned POST like S3; return shared access URL instead
        try:
            from datetime import datetime, timedelta
            from azure.storage.blob import generate_blob_sas, BlobSasPermissions
            
            blob_key = f"tenants/{tenant_id}/{env}/raw/{key}"
            sas_token = generate_blob_sas(
                account_name=self._client.account_name,
                container_name=self._container,
                blob_name=blob_key,
                account_key=self._connection_string.split("AccountKey=")[1],
                permission=BlobSasPermissions(write=True),
                expiry=datetime.utcnow() + timedelta(hours=1),
            )
            
            blob_uri = f"https://{self._client.account_name}.blob.core.windows.net/{self._container}/{blob_key}?{sas_token}"
            return {
                "url": blob_uri,
                "fields": {},  # Blob Storage doesn't use form fields like S3
            }
        except Exception as exc:
            logger.error("Failed to generate presigned URL: %s", exc)
            raise RuntimeError(f"Failed to generate presigned URL: {exc}") from exc


class GCSObjectStoreAdapter:
    """Google Cloud Storage adapter."""
    
    def __init__(
        self,
        project: Optional[str] = None,
        bucket: Optional[str] = None,
    ) -> None:
        if storage is None:
            raise RuntimeError("google-cloud-storage is required for GCS")
        
        from engines.config import runtime_config
        
        self._project = project or runtime_config.get_gcs_project()
        self._bucket = bucket
        
        if not self._project:
            raise RuntimeError("GCP project is required for GCS")
        if not self._bucket:
            import os
            self._bucket = os.getenv("GCS_BUCKET")
        if not self._bucket:
            raise RuntimeError("GCS_BUCKET required for GCS adapter")
        
        try:
            self._client = storage.Client(project=self._project)  # type: ignore
            self._bucket_obj = self._client.bucket(self._bucket)
        except Exception as exc:
            raise RuntimeError(f"Failed to initialize GCS: {exc}") from exc
    
    def put_object(self, key: str, content: bytes, tenant_id: str, env: str) -> str:
        """Store object in GCS with tenant/env namespacing."""
        try:
            # Namespace: tenants/{tenant}/{env}/raw/{key}
            gcs_key = f"tenants/{tenant_id}/{env}/raw/{key}"
            blob = self._bucket_obj.blob(gcs_key)
            blob.upload_from_string(content)
            
            # Return URI
            uri = f"gs://{self._bucket}/{gcs_key}"
            logger.info("Stored GCS object: %s", uri)
            return uri
        except Exception as exc:
            logger.error("Failed to store GCS object: %s", exc)
            raise RuntimeError(f"Failed to store object: {exc}") from exc
    
    def get_object(self, key: str, tenant_id: str, env: str) -> Optional[bytes]:
        """Retrieve object from GCS."""
        try:
            gcs_key = f"tenants/{tenant_id}/{env}/raw/{key}"
            blob = self._bucket_obj.blob(gcs_key)
            return blob.download_as_bytes()
        except Exception as exc:
            logger.warning("Failed to retrieve GCS object: %s", exc)
        return None
    
    def delete_object(self, key: str, tenant_id: str, env: str) -> None:
        """Delete object from GCS."""
        try:
            gcs_key = f"tenants/{tenant_id}/{env}/raw/{key}"
            blob = self._bucket_obj.blob(gcs_key)
            blob.delete()
        except Exception as exc:
            logger.error("Failed to delete GCS object: %s", exc)
            raise RuntimeError(f"Failed to delete object: {exc}") from exc
    
    def list_objects(self, prefix: str, tenant_id: str, env: str) -> list[str]:
        """List objects with prefix from GCS."""
        keys = []
        try:
            prefix_filter = f"tenants/{tenant_id}/{env}/raw/{prefix}"
            for blob in self._client.list_blobs(self._bucket, prefix=prefix_filter):
                keys.append(blob.name)
        except Exception as exc:
            logger.warning("Failed to list GCS objects: %s", exc)
        return keys
    
    def generate_presigned_post(self, key: str, tenant_id: str, env: str) -> dict:
        """Generate presigned POST for client uploads."""
        try:
            from datetime import timedelta
            
            gcs_key = f"tenants/{tenant_id}/{env}/raw/{key}"
            blob = self._bucket_obj.blob(gcs_key)
            
            # Generate presigned POST
            url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(hours=1),
                method="PUT",
            )
            
            return {
                "url": url,
                "fields": {},  # GCS presigned PUT doesn't use form fields
            }
        except Exception as exc:
            logger.error("Failed to generate presigned URL: %s", exc)
            raise RuntimeError(f"Failed to generate presigned URL: {exc}") from exc
