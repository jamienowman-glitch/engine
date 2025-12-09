"""GCS storage helper for raw media and datasets."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, Union

try:
    from google.cloud import storage  # type: ignore
except Exception:  # pragma: no cover
    storage = None

from engines.config import runtime_config

Content = Union[bytes, str, Path]


class GcsClient:
    def __init__(self, client: Any = None) -> None:
        self._client = client or self._default_client()
        cfg = runtime_config.config_snapshot()
        self.raw_bucket = cfg["raw_bucket"]
        self.datasets_bucket = cfg["datasets_bucket"]
        self.tenant_id = cfg["tenant_id"] or ""

    def _default_client(self) -> Any:
        if storage is None:
            raise RuntimeError("google-cloud-storage is not installed")
        project = runtime_config.get_firestore_project()
        return storage.Client(project=project)  # type: ignore[arg-type]

    def _bucket(self, name: Optional[str]):
        if not name:
            raise RuntimeError("Bucket not configured")
        return self._client.bucket(name)

    def _write(self, bucket_name: Optional[str], key: str, content: Content) -> str:
        bucket = self._bucket(bucket_name)
        blob = bucket.blob(key)
        if isinstance(content, Path):
            blob.upload_from_filename(str(content))
        elif isinstance(content, bytes):
            blob.upload_from_string(content)
        else:
            blob.upload_from_string(str(content))
        return f"gs://{bucket_name}/{key}"

    def upload_raw_media(self, tenant_id: str, path: str, content: Content) -> str:
        key = f"{tenant_id}/media/{path}"
        return self._write(self.raw_bucket, key, content)

    def get_raw_media_url(self, tenant_id: str, path: str) -> str:
        bucket = self.raw_bucket or ""
        return f"gs://{bucket}/{tenant_id}/media/{path}"

    def upload_dataset(self, tenant_id: str, path: str, content: Content) -> str:
        key = f"{tenant_id}/datasets/{path}"
        return self._write(self.datasets_bucket, key, content)
