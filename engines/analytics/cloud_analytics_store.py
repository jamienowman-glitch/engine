"""Analytics/Metrics Store cloud backends (Cosmos, DynamoDB, Firestore).

Builder B: Persist tenant/mode/project/app/surface/platform/session_id/request_id/
run_id/step_id/utm_* + payload. Handle GateChain errors (persist with status).
Routed via routing registry (resource_kind=analytics_store).
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Protocol

try:  # pragma: no cover
    from google.cloud import firestore  # type: ignore
except Exception:  # pragma: no cover
    firestore = None

try:  # pragma: no cover
    import boto3  # type: ignore
except Exception:  # pragma: no cover
    boto3 = None

logger = logging.getLogger(__name__)


class AnalyticsRecord:
    """Analytics event record with dimensional and utm tracking."""
    
    def __init__(
        self,
        tenant_id: str,
        mode: str,
        project_id: str,
        app: Optional[str] = None,
        surface: Optional[str] = None,
        platform: Optional[str] = None,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None,
        run_id: Optional[str] = None,
        step_id: Optional[str] = None,
        utm_source: Optional[str] = None,
        utm_medium: Optional[str] = None,
        utm_campaign: Optional[str] = None,
        utm_content: Optional[str] = None,
        utm_term: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        status: str = "success",
        error_message: Optional[str] = None,
    ) -> None:
        self.id = f"{request_id or run_id}#{step_id or 'default'}"
        self.tenant_id = tenant_id
        self.mode = mode
        self.project_id = project_id
        self.app = app
        self.surface = surface
        self.platform = platform
        self.session_id = session_id
        self.request_id = request_id
        self.run_id = run_id
        self.step_id = step_id
        self.utm_source = utm_source
        self.utm_medium = utm_medium
        self.utm_campaign = utm_campaign
        self.utm_content = utm_content
        self.utm_term = utm_term
        self.payload = payload or {}
        self.status = status  # success, gatechainerror, error
        self.error_message = error_message
        self.timestamp = datetime.now(timezone.utc)
    
    def dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "mode": self.mode,
            "project_id": self.project_id,
            "app": self.app,
            "surface": self.surface,
            "platform": self.platform,
            "session_id": self.session_id,
            "request_id": self.request_id,
            "run_id": self.run_id,
            "step_id": self.step_id,
            "utm_source": self.utm_source,
            "utm_medium": self.utm_medium,
            "utm_campaign": self.utm_campaign,
            "utm_content": self.utm_content,
            "utm_term": self.utm_term,
            "payload": self.payload,
            "status": self.status,
            "error_message": self.error_message,
            "timestamp": self.timestamp.isoformat(),
        }


class AnalyticsStore(Protocol):
    """Protocol for analytics store backends."""
    
    def ingest(self, record: AnalyticsRecord) -> None:
        """Ingest analytics event (persist even if failed/error)."""
        ...
    
    def query(
        self,
        tenant_id: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
    ) -> List[AnalyticsRecord]:
        """Query analytics events."""
        ...
    
    def query_by_run(
        self,
        run_id: str,
        tenant_id: str,
    ) -> List[AnalyticsRecord]:
        """Query all events for a run (request/run tracking)."""
        ...


class FirestoreAnalyticsStore:
    """Firestore-backed analytics store."""
    
    def __init__(self, project: Optional[str] = None, client: Optional[object] = None) -> None:
        if firestore is None:
            raise RuntimeError("google-cloud-firestore is required for Firestore analytics store")
        from engines.config import runtime_config
        
        self._project = project or runtime_config.get_firestore_project()
        if not self._project:
            raise RuntimeError("GCP project is required for Firestore analytics store")
        self._client = client or firestore.Client(project=self._project)  # type: ignore[arg-type]
    
    def ingest(self, record: AnalyticsRecord) -> None:
        """Ingest analytics event to Firestore."""
        try:
            # Collection per tenant for isolation
            doc_id = f"{record.request_id or record.run_id}#{record.step_id or 'default'}"
            self._client.collection(f"analytics_{record.tenant_id}").document(doc_id).set(record.dict())
        except Exception as exc:
            logger.error("Firestore analytics ingest failed: %s", exc)
            # Don't raise—persist failed records with error status
            try:
                record.status = "error"
                record.error_message = str(exc)
                doc_id = f"{record.request_id or record.run_id}#{record.step_id or 'default'}"
                self._client.collection(f"analytics_{record.tenant_id}").document(doc_id).set(record.dict())
            except Exception as exc2:
                logger.error("Failed to persist error record: %s", exc2)
    
    def query(
        self,
        tenant_id: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
    ) -> List[AnalyticsRecord]:
        """Query analytics from Firestore."""
        records = []
        try:
            query = self._client.collection(f"analytics_{tenant_id}").order_by("timestamp", direction=firestore.Query.DESCENDING).limit(limit)  # type: ignore
            
            if filters:
                for key, value in filters.items():
                    if key == "status":
                        query = query.where("status", "==", value)
                    elif key == "run_id":
                        query = query.where("run_id", "==", value)
                    elif key == "session_id":
                        query = query.where("session_id", "==", value)
            
            for doc in query.stream():
                try:
                    data = doc.to_dict()
                    record = AnalyticsRecord(**data)
                    records.append(record)
                except Exception as exc:
                    logger.warning("Failed to deserialize analytics record: %s", exc)
        except Exception as exc:
            logger.warning("Firestore analytics query failed: %s", exc)
        
        return records
    
    def query_by_run(self, run_id: str, tenant_id: str) -> List[AnalyticsRecord]:
        """Query all events for a run."""
        return self.query(tenant_id, filters={"run_id": run_id})


class DynamoDBAnalyticsStore:
    """DynamoDB-backed analytics store."""
    
    def __init__(self, table_name: Optional[str] = None, region: Optional[str] = None) -> None:
        if boto3 is None:
            raise RuntimeError("boto3 is required for DynamoDB analytics store")
        
        self._table_name = table_name or "analytics_store"
        self._region = region or "us-west-2"
        
        try:
            dynamodb = boto3.resource("dynamodb", region_name=self._region)  # type: ignore
            self._table = dynamodb.Table(self._table_name)  # type: ignore
        except Exception as exc:
            raise RuntimeError(f"Failed to initialize DynamoDB table: {exc}") from exc
    
    def ingest(self, record: AnalyticsRecord) -> None:
        """Ingest analytics event to DynamoDB."""
        try:
            item = {
                "pk": f"analytics#{record.tenant_id}",
                "sk": f"{record.timestamp.timestamp()}#{record.id}",
                "run_id": record.run_id,
                "data": json.dumps(record.dict(), default=str),
            }
            self._table.put_item(Item=item)
        except Exception as exc:
            logger.error("DynamoDB analytics ingest failed: %s", exc)
            # Try to persist error record
            try:
                record.status = "error"
                record.error_message = str(exc)
                item = {
                    "pk": f"analytics#{record.tenant_id}",
                    "sk": f"{record.timestamp.timestamp()}#{record.id}",
                    "run_id": record.run_id,
                    "data": json.dumps(record.dict(), default=str),
                }
                self._table.put_item(Item=item)
            except Exception as exc2:
                logger.error("Failed to persist error record: %s", exc2)
    
    def query(
        self,
        tenant_id: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
    ) -> List[AnalyticsRecord]:
        """Query analytics from DynamoDB."""
        records = []
        try:
            pk = f"analytics#{tenant_id}"
            
            if filters and "run_id" in filters:
                # Query by run_id (if GSI available)
                expression_values = {":pk": pk, ":run_id": filters["run_id"]}
                response = self._table.query(
                    KeyConditionExpression="pk = :pk",
                    FilterExpression="run_id = :run_id",
                    ExpressionAttributeValues=expression_values,
                    Limit=limit,
                    ScanIndexForward=False,
                )
            else:
                # Full scan with filters
                response = self._table.query(
                    KeyConditionExpression="pk = :pk",
                    ExpressionAttributeValues={":pk": pk},
                    Limit=limit,
                    ScanIndexForward=False,
                )
            
            for item in response.get("Items", []):
                try:
                    data = json.loads(item["data"])
                    record = AnalyticsRecord(**data)
                    records.append(record)
                except Exception as exc:
                    logger.warning("Failed to deserialize analytics record: %s", exc)
        except Exception as exc:
            logger.warning("DynamoDB analytics query failed: %s", exc)
        
        return records
    
    def query_by_run(self, run_id: str, tenant_id: str) -> List[AnalyticsRecord]:
        """Query all events for a run."""
        return self.query(tenant_id, filters={"run_id": run_id})


class CosmosAnalyticsStore:
    """Azure Cosmos DB-backed analytics store."""
    
    def __init__(
        self,
        endpoint: Optional[str] = None,
        key: Optional[str] = None,
        database: str = "analytics_store",
    ) -> None:
        """Initialize Cosmos client."""
        try:
            from azure.cosmos import CosmosClient  # type: ignore
        except ImportError:
            raise RuntimeError("azure-cosmos is required for Cosmos analytics store")
        
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
            self._container = self._db.get_container_client("analytics")
        except Exception as exc:
            raise RuntimeError(f"Failed to initialize Cosmos client: {exc}") from exc
    
    def ingest(self, record: AnalyticsRecord) -> None:
        """Ingest analytics event to Cosmos."""
        try:
            item = {
                "id": f"{record.tenant_id}#{record.id}",
                "partition_key": record.tenant_id,
                **record.dict(),
            }
            self._container.upsert_item(body=item)
        except Exception as exc:
            logger.error("Cosmos analytics ingest failed: %s", exc)
            # Try to persist error record
            try:
                record.status = "error"
                record.error_message = str(exc)
                item = {
                    "id": f"{record.tenant_id}#{record.id}",
                    "partition_key": record.tenant_id,
                    **record.dict(),
                }
                self._container.upsert_item(body=item)
            except Exception as exc2:
                logger.error("Failed to persist error record: %s", exc2)
    
    def query(
        self,
        tenant_id: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
    ) -> List[AnalyticsRecord]:
        """Query analytics from Cosmos."""
        records = []
        try:
            query = "SELECT TOP @limit * FROM c WHERE c.partition_key = @tenant ORDER BY c.timestamp DESC"
            params = [
                {"name": "@tenant", "value": tenant_id},
                {"name": "@limit", "value": limit},
            ]
            
            if filters and "run_id" in filters:
                query = "SELECT TOP @limit * FROM c WHERE c.partition_key = @tenant AND c.run_id = @run_id ORDER BY c.timestamp DESC"
                params.append({"name": "@run_id", "value": filters["run_id"]})
            
            items = list(self._container.query_items(query=query, parameters=params))
            for item in items:
                try:
                    record = AnalyticsRecord(**item)
                    records.append(record)
                except Exception as exc:
                    logger.warning("Failed to deserialize analytics record: %s", exc)
        except Exception as exc:
            logger.warning("Cosmos analytics query failed: %s", exc)
        
        return records
    
    def query_by_run(self, run_id: str, tenant_id: str) -> List[AnalyticsRecord]:
        """Query all events for a run."""
        return self.query(tenant_id, filters={"run_id": run_id})
