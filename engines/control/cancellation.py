"""Cancellation Service for Control Plane."""
from __future__ import annotations

import logging
from typing import Dict, Literal
from fastapi import APIRouter, Depends, HTTPException

from engines.common.identity import RequestContext, get_request_context
from engines.identity.auth import AuthContext, get_auth_context
from engines.realtime.contracts import (
    StreamEvent, RoutingKeys, ActorType, EventPriority, PersistPolicy, EventMeta
)
from engines.chat.service.transport_layer import bus
from engines.chat.contracts import Message, Contact
from datetime import datetime, timezone

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/runs", tags=["control"])

# Stub for run ownership
# run_id -> (tenant_id, thread_id)
run_registry: Dict[str, tuple[str, str]] = {}

# Helper for testing
def register_run(run_id: str, tenant_id: str, thread_id: str):
    run_registry[run_id] = (tenant_id, thread_id)

@router.post("/{run_id}/cancel")
async def cancel_run(
    run_id: str,
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    # 1. Access Check
    if auth_context.default_tenant_id != request_context.tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")

    # 2. Verify Run
    if run_id not in run_registry:
        # In real system this queries DB
        raise HTTPException(status_code=404, detail="Run not found")
    
    owner_tenant, thread_id = run_registry[run_id]
    if owner_tenant != request_context.tenant_id:
        raise HTTPException(status_code=404, detail="Run not found") # Isolation

    # 3. Cancel Logic (Stub)
    logger.info(f"Cancelling run {run_id} for tenant {owner_tenant}")
    
    # 4. Emit 'run_cancelled'
    event = StreamEvent(
        type="run_cancelled",
        routing=RoutingKeys(
            tenant_id=owner_tenant,
            env=request_context.env,
            thread_id=thread_id,
            actor_id=auth_context.user_id,
            actor_type=ActorType.HUMAN
        ),
        ids={"run_id": run_id}, # type: ignore (EventIds kwarg or field assignment)
        # Pydantic v1 vs v2 constructor. StreamEvent defines 'ids: EventIds'.
        # We can pass dict if Pydanic parses it, or use object.
        # Let's use object in Test/Service to be safe.
        data={"run_id": run_id},
        meta=EventMeta(priority=EventPriority.TRUTH, persist=PersistPolicy.ALWAYS)
    )
    
    # Manually fix ids field construction if needed
    # event.ids.run_id = run_id
    # Or cleaner:
    from engines.realtime.contracts import EventIds
    event.ids = EventIds(run_id=run_id)

    # Publish
    msg = Message(
        id=event.event_id,
        thread_id=thread_id,
        sender=Contact(id="system"),
        text=event.json(),
        role="system",
        created_at=datetime.now(timezone.utc)
    )
    
    # Sync bus
    bus.add_message(thread_id, msg) # type: ignore
    
    return {"status": "cancelled", "run_id": run_id}
