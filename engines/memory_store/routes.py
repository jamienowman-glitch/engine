"""HTTP routes for memory_store (MEM-01: routing-only session memory).

Provides:
- POST /memory/set - set session memory key with optional TTL
- GET /memory/get - get session memory value
- DELETE /memory/delete - delete session memory key
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from engines.common.identity import (
    RequestContext,
    get_request_context,
    validate_identity_precedence,
)
from engines.identity.auth import get_auth_context, require_tenant_membership
from engines.memory_store.service_reject import (
    MemoryStoreServiceRejectOnMissing,
    MissingMemoryStoreRoute,
)

router = APIRouter(prefix="/memory", tags=["memory_store"])


# ===== Request/Response Models =====

class SetMemoryRequest(BaseModel):
    """Request to set a memory value."""
    key: str
    value: Any
    ttl_seconds: Optional[int] = None


class SetMemoryResponse(BaseModel):
    """Response to set memory request."""
    key: str
    status: str = "set"


class GetMemoryResponse(BaseModel):
    """Response to get memory request."""
    key: str
    value: Optional[Any] = None
    found: bool


class DeleteMemoryResponse(BaseModel):
    """Response to delete memory request."""
    key: str
    status: str = "deleted"


# ===== Endpoints =====

@router.post("/set", response_model=SetMemoryResponse)
def set_memory(
    payload: SetMemoryRequest,
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    """Set a session memory value with optional TTL.
    
    AUTH-01: Enforces server-derived identity. Client cannot override tenant_id/project_id.
    Raises HTTP 403 (auth.identity_override) on mismatch.
    Raises HTTP 503 (memory_store.missing_route) if route missing.
    """
    require_tenant_membership(auth, context.tenant_id)
    
    # AUTH-01: Identity precedence enforced (no client override of tenant/project)
    # Memory store doesn't accept identity in request body
    
    try:
        svc = MemoryStoreServiceRejectOnMissing(context)
        svc.set(
            key=payload.key,
            value=payload.value,
            ttl_seconds=payload.ttl_seconds,
        )
        return SetMemoryResponse(key=payload.key)
    except MissingMemoryStoreRoute as e:
        raise HTTPException(
            status_code=e.status_code,
            detail={
                "error_code": e.error_code,
                "message": e.message,
            },
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Set failed: {str(e)}")


@router.get("/get", response_model=GetMemoryResponse)
def get_memory(
    key: str = Query(..., description="Memory key"),
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    """Get a session memory value (returns null if not found or expired).
    
    AUTH-01: Server-derived context enforced via RequestContext.
    Raises HTTP 503 (memory_store.missing_route) if route missing.
    """
    require_tenant_membership(auth, context.tenant_id)
    
    try:
        svc = MemoryStoreServiceRejectOnMissing(context)
        value = svc.get(key=key)
        return GetMemoryResponse(key=key, value=value, found=value is not None)
    except MissingMemoryStoreRoute as e:
        raise HTTPException(
            status_code=e.status_code,
            detail={
                "error_code": e.error_code,
                "message": e.message,
            },
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Get failed: {str(e)}")


@router.delete("/delete", response_model=DeleteMemoryResponse)
def delete_memory(
    key: str = Query(..., description="Memory key"),
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    """Delete a session memory value.
    
    AUTH-01: Server-derived context enforced via RequestContext.
    Raises HTTP 503 (memory_store.missing_route) if route missing.
    """
    require_tenant_membership(auth, context.tenant_id)
    
    try:
        svc = MemoryStoreServiceRejectOnMissing(context)
        svc.delete(key=key)
        return DeleteMemoryResponse(key=key)
    except MissingMemoryStoreRoute as e:
        raise HTTPException(
            status_code=e.status_code,
            detail={
                "error_code": e.error_code,
                "message": e.message,
            },
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")
