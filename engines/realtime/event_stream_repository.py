"""Event stream repository with cloud backends (Firestore, DynamoDB, Cosmos).

Builder A: Append/list_after with last_event_id cursor support.
Endpoints are routed via routing registry (resource_kind=event_stream).
"""
from __future__ import annotations

import json
import logging
from typing import Dict, List, Optional, Protocol

from engines.common.identity import RequestContext
from engines.realtime.contracts import StreamEvent

try:  # pragma: no cover
    from google.cloud import firestore  # type: ignore
except Exception:  # pragma: no cover
    firestore = None

try:  # pragma: no cover
    import boto3  # type: ignore
except Exception:  # pragma: no cover
    boto3 = None

logger = logging.getLogger(__name__)


class EventStreamStore(Protocol):
    """Protocol for event stream backends."""
    
    def append(
        self, 
        stream_id: str, 
        event: StreamEvent, 
        context: RequestContext,
    ) -> None:
        """Append event to stream."""
        ...
    
    def list_after(
        self, 
        stream_id: str, 
        after_event_id: Optional[str] = None,
    ) -> List[StreamEvent]:
        """List events after cursor (last_event_id)."""
        ...


class FirestoreEventStreamStore:
    """Firestore-backed event stream with cursor support."""
    
    _collection = "event_streams"
    
    def __init__(self, project: Optional[str] = None, client: Optional[object] = None) -> None:
        if firestore is None:
            raise RuntimeError("google-cloud-firestore is required for Firestore event stream")
        from engines.config import runtime_config
        
        self._project = project or runtime_config.get_firestore_project()
        if not self._project:
            raise RuntimeError("GCP project is required for Firestore event stream")
        self._client = client or firestore.Client(project=self._project)  # type: ignore[arg-type]
    
    def _event_collection(self, stream_id: str):
        """Get events subcollection for stream."""
        return (
            self._client
            .collection(self._collection)
            .document(stream_id)
            .collection("events")
        )
    
    def append(
        self, 
        stream_id: str, 
        event: StreamEvent, 
        context: RequestContext,
    ) -> None:
        """Append event to Firestore."""
        if context is None:
            raise RuntimeError("RequestContext is required for event stream append")
        
        # Store event as JSON doc with event_id as doc key
        doc_data = event.dict()
        doc_data["ts"] = event.ts  # Ensure timestamp ordering
        
        try:
            self._event_collection(stream_id).document(event.event_id).set(doc_data)
        except Exception as exc:
            logger.error("Firestore event stream append failed: %s", exc)
            raise RuntimeError(f"Failed to append event: {exc}") from exc
    
    def list_after(
        self, 
        stream_id: str, 
        after_event_id: Optional[str] = None,
    ) -> List[StreamEvent]:
        """List events from stream, optionally after cursor."""
        events: List[StreamEvent] = []
        
        try:
            collection = self._event_collection(stream_id)
            query = collection.order_by("ts")
            
            # If cursor provided, find it first and return subsequent
            if after_event_id:
                # Fetch all events and find cursor position
                all_snaps = list(query.stream())
                found = False
                for snap in all_snaps:
                    if found:
                        try:
                            events.append(StreamEvent(**snap.to_dict()))
                        except Exception as exc:
                            logger.warning("Failed to deserialize event: %s", exc)
                    if snap.id == after_event_id:
                        found = True
            else:
                # No cursor, return all events
                for snap in query.stream():
                    try:
                        events.append(StreamEvent(**snap.to_dict()))
                    except Exception as exc:
                        logger.warning("Failed to deserialize event: %s", exc)
        except Exception as exc:
            logger.warning("Firestore event stream list failed: %s", exc)
        
        return events


class DynamoDBEventStreamStore:
    """DynamoDB-backed event stream with cursor support."""
    
    def __init__(self, table_name: Optional[str] = None, region: Optional[str] = None) -> None:
        if boto3 is None:
            raise RuntimeError("boto3 is required for DynamoDB event stream")
        
        self._table_name = table_name or "event_streams"
        self._region = region or "us-west-2"
        
        try:
            dynamodb = boto3.resource("dynamodb", region_name=self._region)  # type: ignore
            self._table = dynamodb.Table(self._table_name)  # type: ignore
        except Exception as exc:
            raise RuntimeError(f"Failed to initialize DynamoDB table: {exc}") from exc
    
    def append(
        self, 
        stream_id: str, 
        event: StreamEvent, 
        context: RequestContext,
    ) -> None:
        """Append event to DynamoDB."""
        if context is None:
            raise RuntimeError("RequestContext is required for event stream append")
        
        try:
            item = event.dict()
            item["pk"] = f"stream#{stream_id}"
            item["sk"] = f"event#{event.ts.timestamp()}#{event.event_id}"
            self._table.put_item(Item=item)
        except Exception as exc:
            logger.error("DynamoDB event stream append failed: %s", exc)
            raise RuntimeError(f"Failed to append event: {exc}") from exc
    
    def list_after(
        self, 
        stream_id: str, 
        after_event_id: Optional[str] = None,
    ) -> List[StreamEvent]:
        """List events from DynamoDB, optionally after cursor."""
        events: List[StreamEvent] = []
        
        try:
            pk = f"stream#{stream_id}"
            response = self._table.query(
                KeyConditionExpression="pk = :pk",
                ExpressionAttributeValues={":pk": pk},
                ScanIndexForward=True,  # Sort ascending by sk (timestamp)
            )
            
            items = response.get("Items", [])
            
            # If cursor provided, skip until found
            if after_event_id:
                found = False
                for item in items:
                    if found:
                        try:
                            events.append(StreamEvent(**item))
                        except Exception as exc:
                            logger.warning("Failed to deserialize event: %s", exc)
                    if item.get("event_id") == after_event_id:
                        found = True
            else:
                for item in items:
                    try:
                        events.append(StreamEvent(**item))
                    except Exception as exc:
                        logger.warning("Failed to deserialize event: %s", exc)
        except Exception as exc:
            logger.warning("DynamoDB event stream list failed: %s", exc)
        
        return events


class CosmosEventStreamStore:
    """Azure Cosmos DB-backed event stream with cursor support."""
    
    def __init__(
        self, 
        endpoint: Optional[str] = None, 
        key: Optional[str] = None,
        database: str = "event_streams",
    ) -> None:
        """Initialize Cosmos client.
        
        Endpoint and key can be provided or read from environment:
        AZURE_COSMOSDB_ENDPOINT, AZURE_COSMOSDB_KEY
        """
        try:
            from azure.cosmos import CosmosClient, PartitionKey  # type: ignore
        except ImportError:
            raise RuntimeError("azure-cosmos is required for Cosmos event stream")
        
        self._endpoint = endpoint
        self._key = key
        self._database_name = database
        self._partition_key_path = "/stream_id"
        
        if not self._endpoint or not self._key:
            import os
            self._endpoint = os.getenv("AZURE_COSMOSDB_ENDPOINT")
            self._key = os.getenv("AZURE_COSMOSDB_KEY")
        
        if not self._endpoint or not self._key:
            raise RuntimeError("AZURE_COSMOSDB_ENDPOINT and AZURE_COSMOSDB_KEY required for Cosmos")
        
        try:
            self._client = CosmosClient(self._endpoint, credential=self._key)
            self._db = self._client.get_database_client(database)
            self._container = self._db.get_container_client("events")
        except Exception as exc:
            raise RuntimeError(f"Failed to initialize Cosmos client: {exc}") from exc
    
    def append(
        self, 
        stream_id: str, 
        event: StreamEvent, 
        context: RequestContext,
    ) -> None:
        """Append event to Cosmos."""
        if context is None:
            raise RuntimeError("RequestContext is required for event stream append")
        
        try:
            item = event.dict()
            item["stream_id"] = stream_id
            item["id"] = event.event_id
            self._container.create_item(body=item)
        except Exception as exc:
            logger.error("Cosmos event stream append failed: %s", exc)
            raise RuntimeError(f"Failed to append event: {exc}") from exc
    
    def list_after(
        self, 
        stream_id: str, 
        after_event_id: Optional[str] = None,
    ) -> List[StreamEvent]:
        """List events from Cosmos, optionally after cursor."""
        events: List[StreamEvent] = []
        
        try:
            query = "SELECT * FROM c WHERE c.stream_id = @stream_id ORDER BY c.ts"
            params = [{"name": "@stream_id", "value": stream_id}]
            
            items = list(self._container.query_items(query=query, parameters=params))
            
            # If cursor provided, skip until found
            if after_event_id:
                found = False
                for item in items:
                    if found:
                        try:
                            events.append(StreamEvent(**item))
                        except Exception as exc:
                            logger.warning("Failed to deserialize event: %s", exc)
                    if item.get("event_id") == after_event_id:
                        found = True
            else:
                for item in items:
                    try:
                        events.append(StreamEvent(**item))
                    except Exception as exc:
                        logger.warning("Failed to deserialize event: %s", exc)
        except Exception as exc:
            logger.warning("Cosmos event stream list failed: %s", exc)
        
        return events
