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
from engines.common.error_envelope import error_response, missing_route_error
from engines.identity.auth import get_auth_context, require_tenant_membership
from engines.memory_store.service_reject import (
    MemoryStoreServiceRejectOnMissing,
    MissingMemoryStoreRoute,
)

router = APIRouter(prefix="/memory", tags=["memory_store"])


def _ensure_membership(auth, context: RequestContext) -> None:
    try:
        require_tenant_membership(auth, context.tenant_id)
    except HTTPException as exc:
        error_response(
            code="auth.tenant_membership_required",
            message=str(exc.detail),
            status_code=exc.status_code,
            resource_kind="memory_store",
        )


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
    _ensure_membership(auth, context)
    
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
        missing_route_error(
            resource_kind="memory_store",
            tenant_id=context.tenant_id,
            env=context.env,
            status_code=e.status_code,
        )
    except ValueError as e:
        error_response(
            code="memory_store.invalid_request",
            message=str(e),
            status_code=400,
            resource_kind="memory_store",
        )
    except Exception as e:
        error_response(
            code="memory_store.set_failed",
            message=f"Set failed: {str(e)}",
            status_code=500,
            resource_kind="memory_store",
            details={"key": payload.key},
        )


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
    _ensure_membership(auth, context)
    
    try:
        svc = MemoryStoreServiceRejectOnMissing(context)
        value = svc.get(key=key)
        return GetMemoryResponse(key=key, value=value, found=value is not None)
    except MissingMemoryStoreRoute as e:
        missing_route_error(
            resource_kind="memory_store",
            tenant_id=context.tenant_id,
            env=context.env,
            status_code=e.status_code,
        )
    except ValueError as e:
        error_response(
            code="memory_store.invalid_request",
            message=str(e),
            status_code=400,
            resource_kind="memory_store",
        )
    except Exception as e:
        error_response(
            code="memory_store.get_failed",
            message=f"Get failed: {str(e)}",
            status_code=500,
            resource_kind="memory_store",
            details={"key": key},
        )


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
    _ensure_membership(auth, context)
    
    try:
        svc = MemoryStoreServiceRejectOnMissing(context)
        svc.delete(key=key)
        return DeleteMemoryResponse(key=key)
    except MissingMemoryStoreRoute as e:
        missing_route_error(
            resource_kind="memory_store",
            tenant_id=context.tenant_id,
            env=context.env,
            status_code=e.status_code,
        )
    except ValueError as e:
        error_response(
            code="memory_store.invalid_request",
            message=str(e),
            status_code=400,
            resource_kind="memory_store",
        )
    except Exception as e:
        error_response(
            code="memory_store.delete_failed",
            message=f"Delete failed: {str(e)}",
            status_code=500,
            resource_kind="memory_store",
            details={"key": key},
        )
