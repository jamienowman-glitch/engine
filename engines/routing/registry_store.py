"""Routing registry persistence layer (Firestore/DynamoDB/Cosmos).

Builder A: Persist routes to cloud backend (no filesystem).
resource_kind=routing_registry_store.
"""
from __future__ import annotations

import json
import logging
from typing import Dict, List, Optional, Protocol

from engines.routing.registry import ResourceRoute

try:  # pragma: no cover
    from google.cloud import firestore  # type: ignore
except Exception:  # pragma: no cover
    firestore = None

try:  # pragma: no cover
    import boto3  # type: ignore
except Exception:  # pragma: no cover
    boto3 = None

logger = logging.getLogger(__name__)


class RoutingRegistryStore(Protocol):
    """Protocol for routing registry persistence."""
    
    def load_all(self) -> List[ResourceRoute]:
        """Load all routes from backend."""
        ...
    
    def save(self, route: ResourceRoute) -> None:
        """Save single route."""
        ...
    
    def delete(self, resource_kind: str, tenant_id: str, env: str) -> None:
        """Delete route by resource_kind/tenant_id/env."""
        ...


class FirestoreRoutingRegistryStore:
    """Firestore-backed routing registry persistence."""
    
    _collection = "routing_registry"
    
    def __init__(self, project: Optional[str] = None, client: Optional[object] = None) -> None:
        if firestore is None:
            raise RuntimeError("google-cloud-firestore is required for Firestore routing registry")
        from engines.config import runtime_config
        
        self._project = project or runtime_config.get_firestore_project()
        if not self._project:
            raise RuntimeError("GCP project is required for Firestore routing registry")
        self._client = client or firestore.Client(project=self._project)  # type: ignore[arg-type]
    
    def load_all(self) -> List[ResourceRoute]:
        """Load all routes from Firestore."""
        routes = []
        try:
            for doc in self._client.collection(self._collection).stream():
                try:
                    route_data = doc.to_dict()
                    routes.append(ResourceRoute(**route_data))
                except Exception as exc:
                    logger.warning("Failed to deserialize route %s: %s", doc.id, exc)
        except Exception as exc:
            logger.warning("Firestore load_all failed: %s", exc)
        return routes
    
    def save(self, route: ResourceRoute) -> None:
        """Save route to Firestore."""
        try:
            doc_id = f"{route.resource_kind}#{route.tenant_id}#{route.env}"
            self._client.collection(self._collection).document(doc_id).set(route.dict())
        except Exception as exc:
            logger.error("Firestore save route failed: %s", exc)
            raise RuntimeError(f"Failed to save route: {exc}") from exc
    
    def delete(self, resource_kind: str, tenant_id: str, env: str) -> None:
        """Delete route from Firestore."""
        try:
            doc_id = f"{resource_kind}#{tenant_id}#{env}"
            self._client.collection(self._collection).document(doc_id).delete()
        except Exception as exc:
            logger.error("Firestore delete route failed: %s", exc)
            raise RuntimeError(f"Failed to delete route: {exc}") from exc


class DynamoDBRoutingRegistryStore:
    """DynamoDB-backed routing registry persistence."""
    
    def __init__(self, table_name: Optional[str] = None, region: Optional[str] = None) -> None:
        if boto3 is None:
            raise RuntimeError("boto3 is required for DynamoDB routing registry")
        
        self._table_name = table_name or "routing_registry"
        self._region = region or "us-west-2"
        
        try:
            dynamodb = boto3.resource("dynamodb", region_name=self._region)  # type: ignore
            self._table = dynamodb.Table(self._table_name)  # type: ignore
        except Exception as exc:
            raise RuntimeError(f"Failed to initialize DynamoDB table: {exc}") from exc
    
    def load_all(self) -> List[ResourceRoute]:
        """Load all routes from DynamoDB."""
        routes = []
        try:
            response = self._table.scan()
            for item in response.get("Items", []):
                try:
                    route_data = json.loads(item.get("data", "{}"))
                    routes.append(ResourceRoute(**route_data))
                except Exception as exc:
                    logger.warning("Failed to deserialize route %s: %s", item.get("sk"), exc)
            
            # Handle pagination
            while "LastEvaluatedKey" in response:
                response = self._table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
                for item in response.get("Items", []):
                    try:
                        route_data = json.loads(item.get("data", "{}"))
                        routes.append(ResourceRoute(**route_data))
                    except Exception as exc:
                        logger.warning("Failed to deserialize route %s: %s", item.get("sk"), exc)
        except Exception as exc:
            logger.warning("DynamoDB load_all failed: %s", exc)
        return routes
    
    def save(self, route: ResourceRoute) -> None:
        """Save route to DynamoDB."""
        try:
            item = {
                "pk": "routes",
                "sk": f"{route.resource_kind}#{route.tenant_id}#{route.env}",
                "data": json.dumps(route.dict(), default=str),
            }
            self._table.put_item(Item=item)
        except Exception as exc:
            logger.error("DynamoDB save route failed: %s", exc)
            raise RuntimeError(f"Failed to save route: {exc}") from exc
    
    def delete(self, resource_kind: str, tenant_id: str, env: str) -> None:
        """Delete route from DynamoDB."""
        try:
            self._table.delete_item(
                Key={
                    "pk": "routes",
                    "sk": f"{resource_kind}#{tenant_id}#{env}",
                }
            )
        except Exception as exc:
            logger.error("DynamoDB delete route failed: %s", exc)
            raise RuntimeError(f"Failed to delete route: {exc}") from exc


class CosmosRoutingRegistryStore:
    """Azure Cosmos DB-backed routing registry persistence."""
    
    def __init__(
        self,
        endpoint: Optional[str] = None,
        key: Optional[str] = None,
        database: str = "routing_registry",
    ) -> None:
        """Initialize Cosmos client."""
        try:
            from azure.cosmos import CosmosClient  # type: ignore
        except ImportError:
            raise RuntimeError("azure-cosmos is required for Cosmos routing registry")
        
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
            self._container = self._db.get_container_client("routes")
        except Exception as exc:
            raise RuntimeError(f"Failed to initialize Cosmos client: {exc}") from exc
    
    def load_all(self) -> List[ResourceRoute]:
        """Load all routes from Cosmos."""
        routes = []
        try:
            query = "SELECT * FROM c"
            items = list(self._container.query_items(query=query))
            for item in items:
                try:
                    routes.append(ResourceRoute(**item))
                except Exception as exc:
                    logger.warning("Failed to deserialize route %s: %s", item.get("id"), exc)
        except Exception as exc:
            logger.warning("Cosmos load_all failed: %s", exc)
        return routes
    
    def save(self, route: ResourceRoute) -> None:
        """Save route to Cosmos."""
        try:
            item = {
                "id": f"{route.resource_kind}#{route.tenant_id}#{route.env}",
                "partition_key": route.resource_kind,
                **route.dict(),
            }
            self._container.upsert_item(body=item)
        except Exception as exc:
            logger.error("Cosmos save route failed: %s", exc)
            raise RuntimeError(f"Failed to save route: {exc}") from exc
    
    def delete(self, resource_kind: str, tenant_id: str, env: str) -> None:
        """Delete route from Cosmos."""
        try:
            item_id = f"{resource_kind}#{tenant_id}#{env}"
            self._container.delete_item(item=item_id, partition_key=resource_kind)
        except Exception as exc:
            logger.error("Cosmos delete route failed: %s", exc)
            raise RuntimeError(f"Failed to delete route: {exc}") from exc
