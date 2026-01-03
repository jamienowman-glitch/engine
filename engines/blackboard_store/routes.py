"""BB-01: Blackboard Store HTTP Routes (Versioned Writes + Optimistic Concurrency).

Endpoints:
- POST /blackboard/write — Versioned write with optimistic concurrency
- GET /blackboard/read — Read specific version or latest
- GET /blackboard/list-keys — List all keys in blackboard
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

from engines.common.identity import (
    RequestContext,
    get_request_context,
    validate_identity_precedence,
)
from engines.identity.auth import get_auth_context, require_tenant_membership
from engines.blackboard_store.service_reject import (
    BlackboardStoreServiceRejectOnMissing,
    MissingBlackboardStoreRoute,
)


router = APIRouter(prefix="/api/v1", tags=["blackboard_store"])


# Request/Response Models
class WriteBlackboardRequest(BaseModel):
    """Request to write versioned value to blackboard."""
    key: str = Field(..., description="Unique identifier within run")
    value: Dict[str, Any] = Field(..., description="Value to store (must be JSON-serializable)")
    expected_version: Optional[int] = Field(None, description="Expected version; None = new key")


class WriteBlackboardResponse(BaseModel):
    """Response after write."""
    key: str
    version: int
    created_by: str
    created_at: str
    updated_by: str
    updated_at: str
    status: str = "written"


class ReadBlackboardResponse(BaseModel):
    """Response from read."""
    key: str
    value: Optional[Dict[str, Any]] = None
    version: Optional[int] = None
    created_by: Optional[str] = None
    created_at: Optional[str] = None
    updated_by: Optional[str] = None
    updated_at: Optional[str] = None
    found: bool = False


class ListKeysResponse(BaseModel):
    """Response from list_keys."""
    run_id: str
    keys: list[str]
    count: int


class VersionConflictResponse(BaseModel):
    """Error response for version conflict."""
    error_code: str = "blackboard.version_conflict"
    key: str
    expected_version: int
    current_version: int
    message: str


# Endpoints

@router.post("/blackboard/write", response_model=WriteBlackboardResponse)
async def write_blackboard(
    payload: WriteBlackboardRequest,
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    """Write versioned value to blackboard (optimistic concurrency).
    
    AUTH-01: Enforces server-derived identity. Client cannot override tenant_id/project_id.
    Raises HTTP 403 (auth.identity_override) on mismatch.
    Returns HTTP 409 (Conflict) if expected_version doesn't match current version.
    Returns HTTP 503 if route not configured.
    """
    require_tenant_membership(auth, context.tenant_id)
    
    # AUTH-01: Identity precedence enforced (no client override)
    try:
        svc = BlackboardStoreServiceRejectOnMissing(context)
        result = svc.write(
            key=payload.key,
            value=payload.value,
            expected_version=payload.expected_version,
        )
        
        return WriteBlackboardResponse(
            key=result.get("key"),
            version=result.get("version"),
            created_by=result.get("created_by"),
            created_at=result.get("created_at"),
            updated_by=result.get("updated_by"),
            updated_at=result.get("updated_at"),
        )
    
    except MissingBlackboardStoreRoute as e:
        raise HTTPException(
            status_code=503,
            detail={
                "error_code": e.error_code,
                "message": e.message,
            },
        )
    
    except Exception as e:
        error_msg = str(e)
        
        # Version conflict
        if "version" in error_msg.lower() and "conflict" in error_msg.lower():
            raise HTTPException(
                status_code=409,
                detail={
                    "error_code": "blackboard.version_conflict",
                    "key": payload.key,
                    "message": error_msg,
                },
            )
        
        # Generic error
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "blackboard.write_failed",
                "key": payload.key,
                "message": error_msg,
            },
        )


@router.get("/blackboard/read", response_model=ReadBlackboardResponse)
async def read_blackboard(
    key: str = Query(..., description="Key to read"),
    version: Optional[int] = Query(None, description="Specific version; None = latest"),
    context: RequestContext = Depends(get_auth_context),
):
    """Read versioned value from blackboard.
    
    Returns HTTP 404 if key not found.
    Returns HTTP 503 if route not configured.
    """
    try:
        svc = BlackboardStoreServiceRejectOnMissing(context)
        result = svc.read(key=key, version=version)
        
        if result is None:
            return ReadBlackboardResponse(key=key, found=False)
        
        return ReadBlackboardResponse(
            key=result.get("key"),
            value=result.get("value"),
            version=result.get("version"),
            created_by=result.get("created_by"),
            created_at=result.get("created_at"),
            updated_by=result.get("updated_by"),
            updated_at=result.get("updated_at"),
            found=True,
        )
    
    except MissingBlackboardStoreRoute as e:
        raise HTTPException(
            status_code=503,
            detail={
                "error_code": e.error_code,
                "message": e.message,
            },
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "blackboard.read_failed",
                "key": key,
                "message": str(e),
            },
        )


@router.get("/blackboard/list-keys", response_model=ListKeysResponse)
async def list_blackboard_keys(
    run_id: str = Query(..., description="Run identifier"),
    context: RequestContext = Depends(get_auth_context),
):
    """List all keys in blackboard for given run.
    
    Returns HTTP 503 if route not configured.
    """
    try:
        svc = BlackboardStoreServiceRejectOnMissing(context)
        keys = svc.list_keys(run_id=run_id)
        
        return ListKeysResponse(
            run_id=run_id,
            keys=keys,
            count=len(keys),
        )
    
    except MissingBlackboardStoreRoute as e:
        raise HTTPException(
            status_code=503,
            detail={
                "error_code": e.error_code,
                "message": e.message,
            },
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "blackboard.list_keys_failed",
                "run_id": run_id,
                "message": str(e),
            },
        )
