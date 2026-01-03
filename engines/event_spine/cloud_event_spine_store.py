"""Cloud backend implementations for event_spine (append-only, routed).

Supports Firestore, DynamoDB, Cosmos backends.
All backends implement append-only semantics with identity/causality enforcement.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from uuid import uuid4

from engines.common.identity import RequestContext

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    """Return current timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


# ===== Event Shape / Contract =====

class SpineEvent:
    """Canonical event shape for event_spine (append-only).
    
    Required fields enforced:
    - event_id: unique identifier
    - tenant_id: ownership
    - mode: environment (saas, enterprise, system, lab)
    - timestamp: when event occurred
    - event_type: category (analytics|audit|safety|rl|rlha|tuning|budget|strategy_lock|...)
    - source: where event came from (ui|agent|connector|tool)
    - run_id: provenance identifier
    - route: routing destination (event_spine)
    
    Optional fields:
    - user_id, surface_id, project_id: scoping
    - step_id, parent_event_id: causality
    - trace_id, span_id: distributed tracing
    - payload: event-specific data
    """
    
    def __init__(
        self,
        tenant_id: str,
        mode: str,
        event_type: str,
        source: str,
        run_id: str,
        payload: Optional[Dict[str, Any]] = None,
        event_id: Optional[str] = None,
        timestamp: Optional[str] = None,
        user_id: Optional[str] = None,
        surface_id: Optional[str] = None,
        project_id: Optional[str] = None,
        step_id: Optional[str] = None,
        parent_event_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        span_id: Optional[str] = None,
    ):
        self.event_id = event_id or str(uuid4())
        self.tenant_id = tenant_id
        self.mode = mode
        self.timestamp = timestamp or _now_iso()
        self.event_type = event_type
        self.source = source
        self.run_id = run_id
        self.user_id = user_id
        self.surface_id = surface_id
        self.project_id = project_id
        self.step_id = step_id
        self.parent_event_id = parent_event_id
        self.trace_id = trace_id
        self.span_id = span_id
        self.payload = payload or {}
        self.route = "event_spine"
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize event to dict (storage format)."""
        return {
            "event_id": self.event_id,
            "tenant_id": self.tenant_id,
            "mode": self.mode,
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "source": self.source,
            "run_id": self.run_id,
            "user_id": self.user_id,
            "surface_id": self.surface_id,
            "project_id": self.project_id,
            "step_id": self.step_id,
            "parent_event_id": self.parent_event_id,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "payload": self.payload,
            "route": self.route,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SpineEvent:
        """Deserialize event from dict."""
        return cls(**{k: v for k, v in data.items() if k != "route"})


# ===== Firestore Implementation =====

class FirestoreEventSpineStore:
    """Firestore-backed append-only event spine."""
    
    _collection = "event_spine"
    
    def __init__(self, project: Optional[str] = None, client: Optional[object] = None) -> None:
        try:
            from google.cloud import firestore
        except Exception as exc:
            raise RuntimeError("google-cloud-firestore is required for Firestore event spine") from exc
        
        from engines.config import runtime_config
        
        self._project = project or runtime_config.get_firestore_project()
        if not self._project:
            raise RuntimeError("GCP project is required for Firestore event spine")
        self._client = client or firestore.Client(project=self._project)
    
    def append(self, event: SpineEvent, context: RequestContext) -> None:
        """Append event to spine (insert only, no updates)."""
        if not event.event_id:
            raise ValueError("event_id is required")
        if not event.tenant_id or not event.mode or not event.run_id:
            raise ValueError("tenant_id, mode, and run_id are required")
        
        try:
            doc_data = event.to_dict()
            self._client.collection(self._collection).document(event.event_id).set(doc_data)
            logger.debug(f"Appended event {event.event_id} to Firestore event spine")
        except Exception as exc:
            logger.error(f"Failed to append event to Firestore event spine: {exc}")
            raise RuntimeError(f"Event append failed: {exc}") from exc
    
    def list_events(
        self,
        tenant_id: str,
        run_id: str,
        event_type: Optional[str] = None,
        after_event_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[SpineEvent]:
        """List events from spine (read-only query with cursor support).
        
        Args:
            tenant_id: filter by tenant
            run_id: filter by run
            event_type: optional event type filter
            after_event_id: cursor - only return events after this event_id (by timestamp)
            limit: max events to return
        """
        try:
            query = (
                self._client.collection(self._collection)
                .where("tenant_id", "==", tenant_id)
                .where("run_id", "==", run_id)
            )
            
            if event_type:
                query = query.where("event_type", "==", event_type)
            
            query = query.order_by("timestamp").limit(limit + 1)  # +1 to find cursor position
            
            events = []
            found_cursor = not after_event_id  # If no cursor, start from beginning
            
            for snap in query.stream():
                try:
                    if not found_cursor:
                        if snap.id == after_event_id:
                            found_cursor = True
                        continue
                    
                    events.append(SpineEvent.from_dict(snap.to_dict()))
                    if len(events) >= limit:
                        break
                except Exception as exc:
                    logger.warning(f"Failed to deserialize event: {exc}")
            
            return events
        except Exception as exc:
            logger.error(f"Failed to query event spine: {exc}")
            return []


# ===== DynamoDB Implementation =====

class DynamoDBEventSpineStore:
    """DynamoDB-backed append-only event spine."""
    
    def __init__(self, table_name: Optional[str] = None, region: Optional[str] = None) -> None:
        try:
            import boto3
        except Exception as exc:
            raise RuntimeError("boto3 is required for DynamoDB event spine") from exc
        
        self._table_name = table_name or "event_spine"
        self._region = region or "us-west-2"
        
        try:
            dynamodb = boto3.resource("dynamodb", region_name=self._region)
            self._table = dynamodb.Table(self._table_name)
        except Exception as exc:
            raise RuntimeError(f"Failed to initialize DynamoDB table: {exc}") from exc
    
    def append(self, event: SpineEvent, context: RequestContext) -> None:
        """Append event to spine (insert only)."""
        if not event.event_id:
            raise ValueError("event_id is required")
        if not event.tenant_id or not event.mode or not event.run_id:
            raise ValueError("tenant_id, mode, and run_id are required")
        
        try:
            item = event.to_dict()
            # Add GSI keys for querying by tenant/run
            item["tenant_run_idx"] = f"{event.tenant_id}#{event.run_id}"
            
            self._table.put_item(Item=item)
            logger.debug(f"Appended event {event.event_id} to DynamoDB event spine")
        except Exception as exc:
            logger.error(f"Failed to append event to DynamoDB event spine: {exc}")
            raise RuntimeError(f"Event append failed: {exc}") from exc
    
    def list_events(
        self,
        tenant_id: str,
        run_id: str,
        event_type: Optional[str] = None,
        after_event_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[SpineEvent]:
        """List events from spine (query via GSI with cursor support)."""
        try:
            query_params = {
                "IndexName": "tenant_run_idx",
                "KeyConditionExpression": "tenant_run_idx = :trk",
                "ExpressionAttributeValues": {
                    ":trk": f"{tenant_id}#{run_id}",
                },
                "Limit": limit + 1,  # +1 to find cursor
            }
            
            if event_type:
                query_params["FilterExpression"] = "event_type = :et"
                query_params["ExpressionAttributeValues"][":et"] = event_type
            
            response = self._table.query(**query_params)
            
            events = []
            found_cursor = not after_event_id  # If no cursor, start from beginning
            
            for item in response.get("Items", []):
                try:
                    if not found_cursor:
                        if item.get("event_id") == after_event_id:
                            found_cursor = True
                        continue
                    
                    events.append(SpineEvent.from_dict(item))
                    if len(events) >= limit:
                        break
                except Exception as exc:
                    logger.warning(f"Failed to deserialize event: {exc}")
            
            return events
        except Exception as exc:
            logger.error(f"Failed to query event spine: {exc}")
            return []


# ===== Cosmos DB Implementation =====

class CosmosEventSpineStore:
    """Cosmos DB-backed append-only event spine."""
    
    def __init__(self, endpoint: str, key: str, database: str = "event_spine") -> None:
        try:
            from azure.cosmos import CosmosClient
        except Exception as exc:
            raise RuntimeError("azure-cosmos is required for Cosmos event spine") from exc
        
        try:
            self._client = CosmosClient(endpoint, credential=key)
            self._database = self._client.get_database_client(database)
            self._container = self._database.get_container_client("events")
        except Exception as exc:
            raise RuntimeError(f"Failed to initialize Cosmos client: {exc}") from exc
    
    def append(self, event: SpineEvent, context: RequestContext) -> None:
        """Append event to spine (insert only)."""
        if not event.event_id:
            raise ValueError("event_id is required")
        if not event.tenant_id or not event.mode or not event.run_id:
            raise ValueError("tenant_id, mode, and run_id are required")
        
        try:
            item = event.to_dict()
            item["id"] = event.event_id
            item["partition_key"] = event.tenant_id
            
            self._container.create_item(body=item)
            logger.debug(f"Appended event {event.event_id} to Cosmos event spine")
        except Exception as exc:
            logger.error(f"Failed to append event to Cosmos event spine: {exc}")
            raise RuntimeError(f"Event append failed: {exc}") from exc
    
    def list_events(
        self,
        tenant_id: str,
        run_id: str,
        event_type: Optional[str] = None,
        after_event_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[SpineEvent]:
        """List events from spine (query via SQL with cursor support)."""
        try:
            query = "SELECT * FROM c WHERE c.tenant_id = @tenant_id AND c.run_id = @run_id"
            params = [
                {"name": "@tenant_id", "value": tenant_id},
                {"name": "@run_id", "value": run_id},
            ]
            
            if event_type:
                query += " AND c.event_type = @event_type"
                params.append({"name": "@event_type", "value": event_type})
            
            query += " ORDER BY c.timestamp ASC"
            
            events = []
            found_cursor = not after_event_id  # If no cursor, start from beginning
            
            for item in self._container.query_items(query=query, parameters=params):
                try:
                    if not found_cursor:
                        if item.get("event_id") == after_event_id:
                            found_cursor = True
                        continue
                    
                    events.append(SpineEvent.from_dict(item))
                    if len(events) >= limit:
                        break
                except Exception as exc:
                    logger.warning(f"Failed to deserialize event: {exc}")
            
            return events
        except Exception as exc:
            logger.error(f"Failed to query event spine: {exc}")
            return []
