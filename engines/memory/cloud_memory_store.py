"""Memory store cloud backends (Cosmos, DynamoDB, Firestore).

Builder A: Session/blackboard/maybes scoped by tenant/mode/project/user/session.
Cloud-only (no filesystem). Routed via routing registry (resource_kind=memory_store).
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Protocol

from engines.common.identity import RequestContext
from engines.memory.models import Blackboard, SessionMemory, MessageRecord

try:  # pragma: no cover
    from google.cloud import firestore  # type: ignore
except Exception:  # pragma: no cover
    firestore = None

try:  # pragma: no cover
    import boto3  # type: ignore
except Exception:  # pragma: no cover
    boto3 = None

logger = logging.getLogger(__name__)


class MemoryStore(Protocol):
    """Protocol for memory store backends."""
    
    def save_session(self, session: SessionMemory) -> None:
        """Save or update session memory."""
        ...
    
    def get_session(
        self,
        tenant_id: str,
        mode: str,
        project_id: str,
        user_id: str,
        session_id: str,
    ) -> Optional[SessionMemory]:
        """Fetch session memory."""
        ...
    
    def save_blackboard(self, board: Blackboard) -> None:
        """Save or update blackboard."""
        ...
    
    def get_blackboard(
        self,
        tenant_id: str,
        mode: str,
        project_id: str,
        key: str,
    ) -> Optional[Blackboard]:
        """Fetch blackboard by key."""
        ...
    
    def delete_blackboard(
        self,
        tenant_id: str,
        mode: str,
        project_id: str,
        key: str,
    ) -> None:
        """Delete blackboard."""
        ...


class FirestoreMemoryStore:
    """Firestore-backed memory store."""
    
    def __init__(self, project: Optional[str] = None, client: Optional[object] = None) -> None:
        if firestore is None:
            raise RuntimeError("google-cloud-firestore is required for Firestore memory store")
        from engines.config import runtime_config
        
        self._project = project or runtime_config.get_firestore_project()
        if not self._project:
            raise RuntimeError("GCP project is required for Firestore memory store")
        self._client = client or firestore.Client(project=self._project)  # type: ignore[arg-type]
    
    def save_session(self, session: SessionMemory) -> None:
        """Save session to Firestore."""
        try:
            doc_id = f"{session.tenant_id}#{session.mode}#{session.project_id}#{session.user_id}#{session.session_id}"
            self._client.collection("sessions").document(doc_id).set(session.dict())
        except Exception as exc:
            logger.error("Firestore save_session failed: %s", exc)
            raise RuntimeError(f"Failed to save session: {exc}") from exc
    
    def get_session(
        self,
        tenant_id: str,
        mode: str,
        project_id: str,
        user_id: str,
        session_id: str,
    ) -> Optional[SessionMemory]:
        """Fetch session from Firestore."""
        try:
            doc_id = f"{tenant_id}#{mode}#{project_id}#{user_id}#{session_id}"
            doc = self._client.collection("sessions").document(doc_id).get()
            if doc.exists:
                return SessionMemory(**doc.to_dict())
        except Exception as exc:
            logger.warning("Firestore get_session failed: %s", exc)
        return None
    
    def save_blackboard(self, board: Blackboard) -> None:
        """Save blackboard to Firestore."""
        try:
            doc_id = f"{board.tenant_id}#{board.mode}#{board.project_id}#{board.key}"
            self._client.collection("blackboards").document(doc_id).set(board.dict())
        except Exception as exc:
            logger.error("Firestore save_blackboard failed: %s", exc)
            raise RuntimeError(f"Failed to save blackboard: {exc}") from exc
    
    def get_blackboard(
        self,
        tenant_id: str,
        mode: str,
        project_id: str,
        key: str,
    ) -> Optional[Blackboard]:
        """Fetch blackboard from Firestore."""
        try:
            doc_id = f"{tenant_id}#{mode}#{project_id}#{key}"
            doc = self._client.collection("blackboards").document(doc_id).get()
            if doc.exists:
                return Blackboard(**doc.to_dict())
        except Exception as exc:
            logger.warning("Firestore get_blackboard failed: %s", exc)
        return None
    
    def delete_blackboard(
        self,
        tenant_id: str,
        mode: str,
        project_id: str,
        key: str,
    ) -> None:
        """Delete blackboard from Firestore."""
        try:
            doc_id = f"{tenant_id}#{mode}#{project_id}#{key}"
            self._client.collection("blackboards").document(doc_id).delete()
        except Exception as exc:
            logger.error("Firestore delete_blackboard failed: %s", exc)
            raise RuntimeError(f"Failed to delete blackboard: {exc}") from exc


class DynamoDBMemoryStore:
    """DynamoDB-backed memory store."""
    
    def __init__(self, table_name: Optional[str] = None, region: Optional[str] = None) -> None:
        if boto3 is None:
            raise RuntimeError("boto3 is required for DynamoDB memory store")
        
        self._table_name = table_name or "memory_store"
        self._region = region or "us-west-2"
        
        try:
            dynamodb = boto3.resource("dynamodb", region_name=self._region)  # type: ignore
            self._table = dynamodb.Table(self._table_name)  # type: ignore
        except Exception as exc:
            raise RuntimeError(f"Failed to initialize DynamoDB table: {exc}") from exc
    
    def save_session(self, session: SessionMemory) -> None:
        """Save session to DynamoDB."""
        try:
            item = {
                "pk": f"session#{session.tenant_id}#{session.mode}#{session.project_id}",
                "sk": f"{session.user_id}#{session.session_id}",
                "data": json.dumps(session.dict(), default=str),
            }
            self._table.put_item(Item=item)
        except Exception as exc:
            logger.error("DynamoDB save_session failed: %s", exc)
            raise RuntimeError(f"Failed to save session: {exc}") from exc
    
    def get_session(
        self,
        tenant_id: str,
        mode: str,
        project_id: str,
        user_id: str,
        session_id: str,
    ) -> Optional[SessionMemory]:
        """Fetch session from DynamoDB."""
        try:
            response = self._table.get_item(
                Key={
                    "pk": f"session#{tenant_id}#{mode}#{project_id}",
                    "sk": f"{user_id}#{session_id}",
                }
            )
            if "Item" in response:
                data = json.loads(response["Item"]["data"])
                return SessionMemory(**data)
        except Exception as exc:
            logger.warning("DynamoDB get_session failed: %s", exc)
        return None
    
    def save_blackboard(self, board: Blackboard) -> None:
        """Save blackboard to DynamoDB."""
        try:
            item = {
                "pk": f"blackboard#{board.tenant_id}#{board.mode}#{board.project_id}",
                "sk": board.key,
                "data": json.dumps(board.dict(), default=str),
            }
            self._table.put_item(Item=item)
        except Exception as exc:
            logger.error("DynamoDB save_blackboard failed: %s", exc)
            raise RuntimeError(f"Failed to save blackboard: {exc}") from exc
    
    def get_blackboard(
        self,
        tenant_id: str,
        mode: str,
        project_id: str,
        key: str,
    ) -> Optional[Blackboard]:
        """Fetch blackboard from DynamoDB."""
        try:
            response = self._table.get_item(
                Key={
                    "pk": f"blackboard#{tenant_id}#{mode}#{project_id}",
                    "sk": key,
                }
            )
            if "Item" in response:
                data = json.loads(response["Item"]["data"])
                return Blackboard(**data)
        except Exception as exc:
            logger.warning("DynamoDB get_blackboard failed: %s", exc)
        return None
    
    def delete_blackboard(
        self,
        tenant_id: str,
        mode: str,
        project_id: str,
        key: str,
    ) -> None:
        """Delete blackboard from DynamoDB."""
        try:
            self._table.delete_item(
                Key={
                    "pk": f"blackboard#{tenant_id}#{mode}#{project_id}",
                    "sk": key,
                }
            )
        except Exception as exc:
            logger.error("DynamoDB delete_blackboard failed: %s", exc)
            raise RuntimeError(f"Failed to delete blackboard: {exc}") from exc


class CosmosMemoryStore:
    """Azure Cosmos DB-backed memory store."""
    
    def __init__(
        self,
        endpoint: Optional[str] = None,
        key: Optional[str] = None,
        database: str = "memory_store",
    ) -> None:
        """Initialize Cosmos client."""
        try:
            from azure.cosmos import CosmosClient  # type: ignore
        except ImportError:
            raise RuntimeError("azure-cosmos is required for Cosmos memory store")
        
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
    
    def save_session(self, session: SessionMemory) -> None:
        """Save session to Cosmos."""
        try:
            container = self._db.get_container_client("sessions")
            item = {
                "id": f"{session.tenant_id}#{session.mode}#{session.project_id}#{session.user_id}#{session.session_id}",
                "partition_key": f"{session.tenant_id}#{session.mode}#{session.project_id}",
                **session.dict(),
            }
            container.upsert_item(body=item)
        except Exception as exc:
            logger.error("Cosmos save_session failed: %s", exc)
            raise RuntimeError(f"Failed to save session: {exc}") from exc
    
    def get_session(
        self,
        tenant_id: str,
        mode: str,
        project_id: str,
        user_id: str,
        session_id: str,
    ) -> Optional[SessionMemory]:
        """Fetch session from Cosmos."""
        try:
            container = self._db.get_container_client("sessions")
            item_id = f"{tenant_id}#{mode}#{project_id}#{user_id}#{session_id}"
            item = container.read_item(item=item_id, partition_key=f"{tenant_id}#{mode}#{project_id}")
            return SessionMemory(**item)
        except Exception as exc:
            logger.warning("Cosmos get_session failed: %s", exc)
        return None
    
    def save_blackboard(self, board: Blackboard) -> None:
        """Save blackboard to Cosmos."""
        try:
            container = self._db.get_container_client("blackboards")
            item = {
                "id": f"{board.tenant_id}#{board.mode}#{board.project_id}#{board.key}",
                "partition_key": f"{board.tenant_id}#{board.mode}#{board.project_id}",
                **board.dict(),
            }
            container.upsert_item(body=item)
        except Exception as exc:
            logger.error("Cosmos save_blackboard failed: %s", exc)
            raise RuntimeError(f"Failed to save blackboard: {exc}") from exc
    
    def get_blackboard(
        self,
        tenant_id: str,
        mode: str,
        project_id: str,
        key: str,
    ) -> Optional[Blackboard]:
        """Fetch blackboard from Cosmos."""
        try:
            container = self._db.get_container_client("blackboards")
            item_id = f"{tenant_id}#{mode}#{project_id}#{key}"
            item = container.read_item(item=item_id, partition_key=f"{tenant_id}#{mode}#{project_id}")
            return Blackboard(**item)
        except Exception as exc:
            logger.warning("Cosmos get_blackboard failed: %s", exc)
        return None
    
    def delete_blackboard(
        self,
        tenant_id: str,
        mode: str,
        project_id: str,
        key: str,
    ) -> None:
        """Delete blackboard from Cosmos."""
        try:
            container = self._db.get_container_client("blackboards")
            item_id = f"{tenant_id}#{mode}#{project_id}#{key}"
            container.delete_item(item=item_id, partition_key=f"{tenant_id}#{mode}#{project_id}")
        except Exception as exc:
            logger.error("Cosmos delete_blackboard failed: %s", exc)
            raise RuntimeError(f"Failed to delete blackboard: {exc}") from exc
