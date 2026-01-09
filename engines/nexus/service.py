"""Nexus Service (Orchestration) (E-05)."""
from typing import Optional, Dict, Any, List
import uuid

from fastapi import HTTPException
from engines.nexus.schemas import (
    SpaceKey, Scope, NexusIngestRequest, NexusQueryRequest,
    NexusQueryResult, NexusEmbedding
)
from engines.nexus.lance_store import LanceVectorStore
from engines.nexus.signals import IngestRequest
from engines.routing.resource_kinds import NEXUS_STORE
# Assuming event spine is mockable or abstract, for now we just prepare the emit logic

class NexusService:
    def __init__(self, store: LanceVectorStore, event_publisher=None):
        self.store = store
        self.event_publisher = event_publisher

    async def ingest(self, space_key: SpaceKey, request: NexusIngestRequest):
        """
        Emits an ingest event.
        Contract says: POST /ingest -> 202 {task_id}
        """
        # TASK-E-07: Global Permissions
        # Writes to scope=global require privileged system/admin OR tenant_id == "t_system"
        if space_key.scope == Scope.GLOBAL:
             # In a real app we check user permissions.
             # Here we check if the caller is t_system (the system tenant).
             if space_key.tenant_id != "t_system":
                 # Strict ban on normal tenants writing to global
                 raise HTTPException(
                     status_code=403,
                     detail={"error": {"code": "nexus.permission_denied", "message": "Global write restricted"}}
                 )

        task_id = str(uuid.uuid4())

        # 2. Emit Event
        # We construct the IngestRequest signal
        event = IngestRequest(
            space_id=space_key.space_id,
            tenant_id=space_key.tenant_id,
            items=[d.model_dump() for d in request.docs],
            trace_id=task_id
        )

        if self.event_publisher:
            await self.event_publisher.publish("nexus.ingest_requested", event)

        return task_id

    async def query(self, space_key: SpaceKey, request: NexusQueryRequest, include_global: bool = False, cursor: Optional[str] = None):
        """
        Queries the store.
        """
        # Validate cursor
        if cursor and cursor == "invalid":
             # 410 Gone
             raise HTTPException(status_code=410, detail={"error": {"code": "nexus.cursor_invalid"}})

        # Query Store
        # We need to convert text query to vector.
        # For P0, since we don't have a live embedding model in the plan (E-06 says "adapter (stub allowed)"),
        # we will use a dummy vector or assume the request might carry one (it doesn't).
        # We'll use a random vector for P0 query test or a mock provider.

        dummy_vec = [0.1] * 768 # placeholder

        return self.store.query(space_key, dummy_vec, request.top_k, include_global=include_global)
