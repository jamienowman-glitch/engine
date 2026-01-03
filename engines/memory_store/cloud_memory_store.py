"""Cloud backend implementations for memory_store (persistent session memory).

Supports Firestore, DynamoDB, Cosmos backends with TTL.
Scoped to: tenant / mode / project / user / session.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from engines.common.identity import RequestContext

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    """Return current timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


def _add_ttl(seconds: Optional[int]) -> Optional[datetime]:
    """Calculate expiry datetime from TTL seconds."""
    if not seconds or seconds <= 0:
        return None
    return datetime.now(timezone.utc) + timedelta(seconds=seconds)


# ===== Firestore Implementation =====

class FirestoreMemoryStore:
    """Firestore-backed persistent session memory with TTL."""
    
    _collection = "memory_store"
    
    def __init__(self, project: Optional[str] = None, client: Optional[object] = None) -> None:
        try:
            from google.cloud import firestore
        except Exception as exc:
            raise RuntimeError("google-cloud-firestore is required for Firestore memory store") from exc
        
        from engines.config import runtime_config
        
        self._project = project or runtime_config.get_firestore_project()
        if not self._project:
            raise RuntimeError("GCP project is required for Firestore memory store")
        self._client = client or firestore.Client(project=self._project)
    
    def _document_id(self, tenant_id: str, mode: str, user_id: str, key: str) -> str:
        """Generate document ID from scope."""
        return f"{tenant_id}#{mode}#{user_id}#{key}"
    
    def set(
        self,
        key: str,
        value: Any,
        context: RequestContext,
        ttl_seconds: Optional[int] = None,
    ) -> None:
        """Set a value in session memory with optional TTL."""
        if not key:
            raise ValueError("key is required")
        if not context.user_id:
            raise ValueError("user_id is required (from context)")
        
        doc_id = self._document_id(context.tenant_id, context.mode, context.user_id, key)
        
        doc_data = {
            "key": key,
            "value": value,
            "tenant_id": context.tenant_id,
            "mode": context.mode,
            "user_id": context.user_id,
            "project_id": context.project_id,
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
        }
        
        if ttl_seconds and ttl_seconds > 0:
            doc_data["ttl_seconds"] = ttl_seconds
            doc_data["expires_at"] = _add_ttl(ttl_seconds).isoformat() if _add_ttl(ttl_seconds) else None
        
        try:
            self._client.collection(self._collection).document(doc_id).set(doc_data)
            logger.debug(f"Set memory key '{key}' for user {context.user_id}")
        except Exception as exc:
            logger.error(f"Failed to set memory key '{key}': {exc}")
            raise RuntimeError(f"Memory set failed: {exc}") from exc
    
    def get(self, key: str, context: RequestContext) -> Optional[Any]:
        """Get a value from session memory (checks TTL)."""
        if not key:
            raise ValueError("key is required")
        if not context.user_id:
            raise ValueError("user_id is required (from context)")
        
        doc_id = self._document_id(context.tenant_id, context.mode, context.user_id, key)
        
        try:
            doc = self._client.collection(self._collection).document(doc_id).get()
            
            if not doc.exists:
                return None
            
            data = doc.to_dict()
            
            # Check TTL
            if "expires_at" in data and data["expires_at"]:
                expires_at = datetime.fromisoformat(data["expires_at"])
                if datetime.now(timezone.utc) > expires_at:
                    # Expired; delete and return None
                    self._client.collection(self._collection).document(doc_id).delete()
                    logger.debug(f"Memory key '{key}' expired and deleted")
                    return None
            
            return data.get("value")
        except Exception as exc:
            logger.error(f"Failed to get memory key '{key}': {exc}")
            return None
    
    def delete(self, key: str, context: RequestContext) -> None:
        """Delete a value from session memory."""
        if not key:
            raise ValueError("key is required")
        if not context.user_id:
            raise ValueError("user_id is required (from context)")
        
        doc_id = self._document_id(context.tenant_id, context.mode, context.user_id, key)
        
        try:
            self._client.collection(self._collection).document(doc_id).delete()
            logger.debug(f"Deleted memory key '{key}' for user {context.user_id}")
        except Exception as exc:
            logger.error(f"Failed to delete memory key '{key}': {exc}")
            raise RuntimeError(f"Memory delete failed: {exc}") from exc


# ===== DynamoDB Implementation =====

class DynamoDBMemoryStore:
    """DynamoDB-backed persistent session memory with TTL."""
    
    def __init__(self, table_name: Optional[str] = None, region: Optional[str] = None) -> None:
        try:
            import boto3
        except Exception as exc:
            raise RuntimeError("boto3 is required for DynamoDB memory store") from exc
        
        self._table_name = table_name or "memory_store"
        self._region = region or "us-west-2"
        
        try:
            dynamodb = boto3.resource("dynamodb", region_name=self._region)
            self._table = dynamodb.Table(self._table_name)
        except Exception as exc:
            raise RuntimeError(f"Failed to initialize DynamoDB table: {exc}") from exc
    
    def _key(self, tenant_id: str, mode: str, user_id: str, key: str) -> str:
        """Generate composite key from scope."""
        return f"{tenant_id}#{mode}#{user_id}#{key}"
    
    def set(
        self,
        key: str,
        value: Any,
        context: RequestContext,
        ttl_seconds: Optional[int] = None,
    ) -> None:
        """Set a value in session memory with optional TTL."""
        if not key:
            raise ValueError("key is required")
        if not context.user_id:
            raise ValueError("user_id is required (from context)")
        
        composite_key = self._key(context.tenant_id, context.mode, context.user_id, key)
        
        item = {
            "pk": composite_key,
            "key": key,
            "value": value,
            "tenant_id": context.tenant_id,
            "mode": context.mode,
            "user_id": context.user_id,
            "project_id": context.project_id or "none",
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
        }
        
        # DynamoDB TTL is timestamp in seconds, set on table configuration
        if ttl_seconds and ttl_seconds > 0:
            expiry = _add_ttl(ttl_seconds)
            if expiry:
                item["expires_at"] = int(expiry.timestamp())
        
        try:
            self._table.put_item(Item=item)
            logger.debug(f"Set memory key '{key}' for user {context.user_id}")
        except Exception as exc:
            logger.error(f"Failed to set memory key '{key}': {exc}")
            raise RuntimeError(f"Memory set failed: {exc}") from exc
    
    def get(self, key: str, context: RequestContext) -> Optional[Any]:
        """Get a value from session memory (checks TTL)."""
        if not key:
            raise ValueError("key is required")
        if not context.user_id:
            raise ValueError("user_id is required (from context)")
        
        composite_key = self._key(context.tenant_id, context.mode, context.user_id, key)
        
        try:
            response = self._table.get_item(Key={"pk": composite_key})
            
            if "Item" not in response:
                return None
            
            item = response["Item"]
            
            # Check TTL (manual check if TTL stream not set)
            if "expires_at" in item:
                import time
                if int(time.time()) > item["expires_at"]:
                    # Expired; delete and return None
                    self._table.delete_item(Key={"pk": composite_key})
                    logger.debug(f"Memory key '{key}' expired and deleted")
                    return None
            
            return item.get("value")
        except Exception as exc:
            logger.error(f"Failed to get memory key '{key}': {exc}")
            return None
    
    def delete(self, key: str, context: RequestContext) -> None:
        """Delete a value from session memory."""
        if not key:
            raise ValueError("key is required")
        if not context.user_id:
            raise ValueError("user_id is required (from context)")
        
        composite_key = self._key(context.tenant_id, context.mode, context.user_id, key)
        
        try:
            self._table.delete_item(Key={"pk": composite_key})
            logger.debug(f"Deleted memory key '{key}' for user {context.user_id}")
        except Exception as exc:
            logger.error(f"Failed to delete memory key '{key}': {exc}")
            raise RuntimeError(f"Memory delete failed: {exc}") from exc


# ===== Cosmos DB Implementation =====

class CosmosMemoryStore:
    """Cosmos DB-backed persistent session memory with TTL."""
    
    def __init__(self, endpoint: str, key: str, database: str = "memory_store") -> None:
        try:
            from azure.cosmos import CosmosClient
        except Exception as exc:
            raise RuntimeError("azure-cosmos is required for Cosmos memory store") from exc
        
        try:
            self._client = CosmosClient(endpoint, credential=key)
            self._database = self._client.get_database_client(database)
            self._container = self._database.get_container_client("session_memory")
        except Exception as exc:
            raise RuntimeError(f"Failed to initialize Cosmos client: {exc}") from exc
    
    def _document_id(self, tenant_id: str, mode: str, user_id: str, key: str) -> str:
        """Generate document ID from scope."""
        return f"{tenant_id}#{mode}#{user_id}#{key}"
    
    def set(
        self,
        key: str,
        value: Any,
        context: RequestContext,
        ttl_seconds: Optional[int] = None,
    ) -> None:
        """Set a value in session memory with optional TTL."""
        if not key:
            raise ValueError("key is required")
        if not context.user_id:
            raise ValueError("user_id is required (from context)")
        
        doc_id = self._document_id(context.tenant_id, context.mode, context.user_id, key)
        
        item = {
            "id": doc_id,
            "partition_key": context.user_id,
            "key": key,
            "value": value,
            "tenant_id": context.tenant_id,
            "mode": context.mode,
            "user_id": context.user_id,
            "project_id": context.project_id,
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
        }
        
        # Cosmos DB TTL is in seconds
        if ttl_seconds and ttl_seconds > 0:
            item["ttl"] = ttl_seconds
        
        try:
            self._container.upsert_item(body=item)
            logger.debug(f"Set memory key '{key}' for user {context.user_id}")
        except Exception as exc:
            logger.error(f"Failed to set memory key '{key}': {exc}")
            raise RuntimeError(f"Memory set failed: {exc}") from exc
    
    def get(self, key: str, context: RequestContext) -> Optional[Any]:
        """Get a value from session memory (Cosmos TTL automatic)."""
        if not key:
            raise ValueError("key is required")
        if not context.user_id:
            raise ValueError("user_id is required (from context)")
        
        doc_id = self._document_id(context.tenant_id, context.mode, context.user_id, key)
        
        try:
            item = self._container.read_item(item=doc_id, partition_key=context.user_id)
            return item.get("value")
        except Exception as exc:
            # Document may not exist or be expired (Cosmos auto-deletes)
            return None
    
    def delete(self, key: str, context: RequestContext) -> None:
        """Delete a value from session memory."""
        if not key:
            raise ValueError("key is required")
        if not context.user_id:
            raise ValueError("user_id is required (from context)")
        
        doc_id = self._document_id(context.tenant_id, context.mode, context.user_id, key)
        
        try:
            self._container.delete_item(item=doc_id, partition_key=context.user_id)
            logger.debug(f"Deleted memory key '{key}' for user {context.user_id}")
        except Exception as exc:
            logger.error(f"Failed to delete memory key '{key}': {exc}")
            raise RuntimeError(f"Memory delete failed: {exc}") from exc
