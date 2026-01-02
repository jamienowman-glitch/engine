"""Raw Storage repository interface and S3 implementation."""
from __future__ import annotations

from typing import Dict, Protocol, Tuple

import boto3
from botocore.exceptions import ClientError
from fastapi import HTTPException

from engines.config import runtime_config
from engines.nexus.raw_storage.models import RawAsset
import re

_TENANT_PATTERN = re.compile(r"^t_[a-z0-9_-]+$")
_VALID_ENVS = {"dev", "staging", "prod", "stage"}


class RawStorageRepository(Protocol):
    """Abstract interface for raw asset storage."""

    def generate_presigned_post(
        self, tenant_id: str, env: str, asset_id: str, filename: str, content_type: str
    ) -> Tuple[str, Dict[str, str]]:
        """
        Generate a presigned POST for client-side upload.
        Returns (url, fields).
        """
        ...

    def persist_metadata(self, asset: RawAsset) -> None:
        """Persist asset metadata to catalog (in-memory or durable)."""
        ...


class S3RawStorageRepository:
    """S3-backed storage repository.
    
    GAP-G3: Enforce RAW_BUCKET at startup (fail-fast).
    - No deferred checks; bucket must exist in config at init time
    - Prevents runtime errors on first upload
    """

    def __init__(self, bucket_name: str | None = None):
        self.bucket_name = bucket_name or runtime_config.get_raw_bucket()
        if not self.bucket_name:
            raise ValueError(
                "RAW_BUCKET config missing. "
                "Set RAW_BUCKET env var to S3 bucket name for raw storage."
            )

    def _get_bucket(self) -> str:
        # Bucket guaranteed to exist at init time (GAP-G3 fail-fast)
        return self.bucket_name

    def _get_key(self, tenant_id: str, env: str, asset_id: str, filename: str) -> str:
        """Determines (and validates) the storage key."""
        self._validate_tenant(tenant_id)
        self._validate_env(env)
        # Hard-enforce tenancy in path structure
        return f"tenants/{tenant_id}/{env}/raw/{asset_id}/{filename}"

    @staticmethod
    def _validate_tenant(tenant_id: str) -> None:
        if not tenant_id or not _TENANT_PATTERN.match(tenant_id):
            raise HTTPException(status_code=400, detail="invalid tenant_id")

    @staticmethod
    def _validate_env(env: str) -> None:
        normalized = env.lower()
        if normalized not in _VALID_ENVS:
            raise HTTPException(status_code=400, detail="invalid env")

    def generate_presigned_post(
        self, tenant_id: str, env: str, asset_id: str, filename: str, content_type: str
    ) -> Tuple[str, Dict[str, str]]:
        bucket = self._get_bucket()
        key = self._get_key(tenant_id, env, asset_id, filename)
        
        s3 = boto3.client("s3")
        try:
            # Generate presigned POST with 1 hour expiry
            response = s3.generate_presigned_post(
                Bucket=bucket,
                Key=key,
                Fields={"Content-Type": content_type},
                Conditions=[
                    {"bucket": bucket},
                    {"key": key},
                    ["content-length-range", 1, 104857600],  # 100MB limit default
                    {"Content-Type": content_type},
                ],
                ExpiresIn=3600,
            )
            return response["url"], response["fields"]
        except ClientError as e:
            raise HTTPException(status_code=500, detail=f"S3 generation failed: {e}")

    def get_uri(self, tenant_id: str, env: str, asset_id: str, filename: str) -> str:
        """Constructs the S3 URI for the asset."""
        bucket = self._get_bucket()
        key = self._get_key(tenant_id, env, asset_id, filename)
        return f"s3://{bucket}/{key}"

    def persist_metadata(self, asset: RawAsset) -> None:
        # S3 repo only handles blobs; metadata persistence is not yet implemented for S3/Dynamo
        # This is a no-op placeholder for Lane 2 transparency
        pass

    def put_object(
        self, 
        key: str, 
        content: bytes, 
        tenant_id: str = "t_system",
        env: str = "dev",
    ) -> str:
        """Store a blob to S3 and return its URI.
        
        Direct PUT operation (not presigned). Requires AWS credentials.
        Args:
            key: object key (may include / for nested paths)
            content: binary blob
            tenant_id: tenant ID for path validation
            env: environment for path validation
        
        Returns:
            S3 URI (s3://bucket/key)
        """
        self._validate_tenant(tenant_id)
        self._validate_env(env)
        
        bucket = self._get_bucket()
        # For direct put, allow more flexible key structure
        full_key = f"tenants/{tenant_id}/{env}/raw/{key}"
        
        s3 = boto3.client("s3")
        try:
            s3.put_object(
                Bucket=bucket,
                Key=full_key,
                Body=content,
            )
            return f"s3://{bucket}/{full_key}"
        except ClientError as e:
            raise HTTPException(status_code=500, detail=f"S3 PUT failed: {e}")

    def get_object(
        self, 
        key: str, 
        tenant_id: str = "t_system",
        env: str = "dev",
    ) -> bytes | None:
        """Retrieve a blob from S3.
        
        Args:
            key: object key
            tenant_id: tenant ID for path validation
            env: environment for path validation
        
        Returns:
            Binary blob, or None if not found
        """
        self._validate_tenant(tenant_id)
        self._validate_env(env)
        
        bucket = self._get_bucket()
        full_key = f"tenants/{tenant_id}/{env}/raw/{key}"
        
        s3 = boto3.client("s3")
        try:
            response = s3.get_object(Bucket=bucket, Key=full_key)
            return response["Body"].read()
        except s3.exceptions.NoSuchKey:
            return None
        except ClientError as e:
            raise HTTPException(status_code=500, detail=f"S3 GET failed: {e}")


class InMemoryRawStorageRepository:
    """In-memory storage for testing metadata persistence."""

    def __init__(self, bucket_name: str | None = None) -> None:
        self.bucket_name = bucket_name or "test-mem-bucket"
        self.metadata_store: Dict[str, RawAsset] = {}

    def generate_presigned_post(
        self, tenant_id: str, env: str, asset_id: str, filename: str, content_type: str
    ) -> Tuple[str, Dict[str, str]]:
        return (f"https://{self.bucket_name}.s3.amazonaws.com", {"key": f"tenants/{tenant_id}/{env}/raw/{asset_id}/{filename}"})

    def persist_metadata(self, asset: RawAsset) -> None:
        self.metadata_store[asset.asset_id] = asset
