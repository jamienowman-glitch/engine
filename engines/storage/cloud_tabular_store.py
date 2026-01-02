"""Tabular store cloud backends (Cosmos, DynamoDB, Firestore).

Builder A: PK/SK JSON CRUD for configs and registries.
Routed via routing registry (resource_kind=tabular_store).
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Protocol

from engines.common.identity import RequestContext

try:  # pragma: no cover
    from google.cloud import firestore  # type: ignore
except Exception:  # pragma: no cover
    firestore = None

try:  # pragma: no cover
    import boto3  # type: ignore
except Exception:  # pragma: no cover
    boto3 = None

logger = logging.getLogger(__name__)


class TabularStore(Protocol):
    """Protocol for tabular store backends."""
    
    def upsert(
        self,
        table_name: str,
        key: str,
        data: Dict[str, Any],
        context: RequestContext,
    ) -> None:
        """Insert or update record."""
        ...
    
    def get(
        self,
        table_name: str,
        key: str,
        context: RequestContext,
    ) -> Optional[Dict[str, Any]]:
        """Get record by key."""
        ...
    
    def list_by_prefix(
        self,
        table_name: str,
        key_prefix: str,
        context: RequestContext,
    ) -> List[Dict[str, Any]]:
        """List records with keys matching prefix."""
        ...
    
    def delete(
        self,
        table_name: str,
        key: str,
        context: RequestContext,
    ) -> None:
        """Delete record by key."""
        ...


class FirestoreTabularStore:
    """Firestore-backed tabular store."""
    
    def __init__(self, project: Optional[str] = None, client: Optional[object] = None) -> None:
        if firestore is None:
            raise RuntimeError("google-cloud-firestore is required for Firestore tabular store")
        from engines.config import runtime_config
        
        self._project = project or runtime_config.get_firestore_project()
        if not self._project:
            raise RuntimeError("GCP project is required for Firestore tabular store")
        self._client = client or firestore.Client(project=self._project)  # type: ignore[arg-type]
    
    def upsert(
        self,
        table_name: str,
        key: str,
        data: Dict[str, Any],
        context: RequestContext,
    ) -> None:
        """Upsert record to Firestore."""
        try:
            doc_data = {"key": key, **data}
            self._client.collection(table_name).document(key).set(doc_data)
        except Exception as exc:
            logger.error("Firestore upsert failed: %s", exc)
            raise RuntimeError(f"Failed to upsert: {exc}") from exc
    
    def get(
        self,
        table_name: str,
        key: str,
        context: RequestContext,
    ) -> Optional[Dict[str, Any]]:
        """Get record from Firestore."""
        try:
            doc = self._client.collection(table_name).document(key).get()
            if doc.exists:
                return doc.to_dict()
        except Exception as exc:
            logger.warning("Firestore get failed: %s", exc)
        return None
    
    def list_by_prefix(
        self,
        table_name: str,
        key_prefix: str,
        context: RequestContext,
    ) -> List[Dict[str, Any]]:
        """List records with key prefix from Firestore."""
        records = []
        try:
            # Firestore range query: >= prefix and < prefix + next byte
            end_key = key_prefix[:-1] + chr(ord(key_prefix[-1]) + 1)
            query = (
                self._client.collection(table_name)
                .where("key", ">=", key_prefix)
                .where("key", "<", end_key)
            )
            for doc in query.stream():
                records.append(doc.to_dict())
        except Exception as exc:
            logger.warning("Firestore list_by_prefix failed: %s", exc)
        return records
    
    def delete(
        self,
        table_name: str,
        key: str,
        context: RequestContext,
    ) -> None:
        """Delete record from Firestore."""
        try:
            self._client.collection(table_name).document(key).delete()
        except Exception as exc:
            logger.error("Firestore delete failed: %s", exc)
            raise RuntimeError(f"Failed to delete: {exc}") from exc


class DynamoDBTabularStore:
    """DynamoDB-backed tabular store with prefix support."""
    
    def __init__(self, table_name: Optional[str] = None, region: Optional[str] = None) -> None:
        if boto3 is None:
            raise RuntimeError("boto3 is required for DynamoDB tabular store")
        
        self._table_name = table_name or "tabular_store"
        self._region = region or "us-west-2"
        
        try:
            dynamodb = boto3.resource("dynamodb", region_name=self._region)  # type: ignore
            self._table = dynamodb.Table(self._table_name)  # type: ignore
        except Exception as exc:
            raise RuntimeError(f"Failed to initialize DynamoDB table: {exc}") from exc
    
    def upsert(
        self,
        table_name: str,
        key: str,
        data: Dict[str, Any],
        context: RequestContext,
    ) -> None:
        """Upsert record to DynamoDB."""
        try:
            item = {
                "pk": f"{table_name}#{key}",
                "sk": key,
                "table_name": table_name,
                "data": json.dumps(data),
            }
            self._table.put_item(Item=item)
        except Exception as exc:
            logger.error("DynamoDB upsert failed: %s", exc)
            raise RuntimeError(f"Failed to upsert: {exc}") from exc
    
    def get(
        self,
        table_name: str,
        key: str,
        context: RequestContext,
    ) -> Optional[Dict[str, Any]]:
        """Get record from DynamoDB."""
        try:
            response = self._table.get_item(Key={"pk": f"{table_name}#{key}", "sk": key})
            if "Item" in response:
                item = response["Item"]
                return json.loads(item.get("data", "{}"))
        except Exception as exc:
            logger.warning("DynamoDB get failed: %s", exc)
        return None
    
    def list_by_prefix(
        self,
        table_name: str,
        key_prefix: str,
        context: RequestContext,
    ) -> List[Dict[str, Any]]:
        """List records with key prefix from DynamoDB."""
        records = []
        try:
            pk = f"{table_name}#"
            response = self._table.query(
                KeyConditionExpression="pk = :pk AND sk BETWEEN :start AND :end",
                ExpressionAttributeValues={
                    ":pk": pk,
                    ":start": key_prefix,
                    ":end": key_prefix + "~",  # ~ is after most printable chars
                },
            )
            for item in response.get("Items", []):
                records.append(json.loads(item.get("data", "{}")))
        except Exception as exc:
            logger.warning("DynamoDB list_by_prefix failed: %s", exc)
        return records
    
    def delete(
        self,
        table_name: str,
        key: str,
        context: RequestContext,
    ) -> None:
        """Delete record from DynamoDB."""
        try:
            self._table.delete_item(Key={"pk": f"{table_name}#{key}", "sk": key})
        except Exception as exc:
            logger.error("DynamoDB delete failed: %s", exc)
            raise RuntimeError(f"Failed to delete: {exc}") from exc


class CosmosTabularStore:
    """Azure Cosmos DB-backed tabular store."""
    
    def __init__(
        self,
        endpoint: Optional[str] = None,
        key: Optional[str] = None,
        database: str = "tabular_store",
    ) -> None:
        """Initialize Cosmos client."""
        try:
            from azure.cosmos import CosmosClient  # type: ignore
        except ImportError:
            raise RuntimeError("azure-cosmos is required for Cosmos tabular store")
        
        self._endpoint = endpoint
        self._key = key
        self._database_name = database
        
        if not self._endpoint or not self._key:
            import os
            self._endpoint = os.getenv("AZURE_COSMOSDB_ENDPOINT")
            self._key = os.getenv("AZURE_COSMOSDB_KEY")
        
        if not self._endpoint or not self._key:
            raise RuntimeError("AZURE_COSMOSDB_ENDPOINT and AZURE_COSMOSDB_KEY required for Cosmos")
        
        try:
            self._client = CosmosClient(self._endpoint, credential=self._key)
            self._db = self._client.get_database_client(database)
        except Exception as exc:
            raise RuntimeError(f"Failed to initialize Cosmos client: {exc}") from exc
    
    def _get_container(self, table_name: str):
        """Get or create container for table."""
        try:
            return self._db.get_container_client(table_name)
        except Exception:
            # Container might not exist; return client (will fail on operation if truly missing)
            return self._db.get_container_client(table_name)
    
    def upsert(
        self,
        table_name: str,
        key: str,
        data: Dict[str, Any],
        context: RequestContext,
    ) -> None:
        """Upsert record to Cosmos."""
        try:
            container = self._get_container(table_name)
            item = {"id": key, "key": key, **data}
            container.upsert_item(body=item)
        except Exception as exc:
            logger.error("Cosmos upsert failed: %s", exc)
            raise RuntimeError(f"Failed to upsert: {exc}") from exc
    
    def get(
        self,
        table_name: str,
        key: str,
        context: RequestContext,
    ) -> Optional[Dict[str, Any]]:
        """Get record from Cosmos."""
        try:
            container = self._get_container(table_name)
            item = container.read_item(item=key, partition_key=key)
            return item
        except Exception as exc:
            logger.warning("Cosmos get failed: %s", exc)
        return None
    
    def list_by_prefix(
        self,
        table_name: str,
        key_prefix: str,
        context: RequestContext,
    ) -> List[Dict[str, Any]]:
        """List records with key prefix from Cosmos."""
        records = []
        try:
            container = self._get_container(table_name)
            query = "SELECT * FROM c WHERE STARTSWITH(c.key, @prefix)"
            items = list(container.query_items(
                query=query,
                parameters=[{"name": "@prefix", "value": key_prefix}],
            ))
            records.extend(items)
        except Exception as exc:
            logger.warning("Cosmos list_by_prefix failed: %s", exc)
        return records
    
    def delete(
        self,
        table_name: str,
        key: str,
        context: RequestContext,
    ) -> None:
        """Delete record from Cosmos."""
        try:
            container = self._get_container(table_name)
            container.delete_item(item=key, partition_key=key)
        except Exception as exc:
            logger.error("Cosmos delete failed: %s", exc)
            raise RuntimeError(f"Failed to delete: {exc}") from exc
