"""Raw Storage API Routes (PHASE_02 enforcement: RequestContext + AuthContext)."""
from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, Body, HTTPException, Query, Request

from engines.common.error_envelope import error_response

from engines.common.identity import (
    RequestContext,
    assert_context_matches,
    get_request_context,
)
from engines.identity.auth import AuthContext, get_auth_context
from engines.nexus.hardening.auth import enforce_tenant_context
from engines.nexus.hardening.gate_chain import GateChain, get_gate_chain
from engines.nexus.raw_storage.models import RawAsset
from engines.nexus.raw_storage.routing_service import ObjectStoreService
from engines.routing.manager import ForbiddenBackendClass

router = APIRouter(prefix="/nexus/raw", tags=["nexus_raw_storage"])


def get_service() -> ObjectStoreService:
    """Get ObjectStoreService with routing-based backend resolution."""
    return ObjectStoreService()


from engines.common.error_envelope import error_response

# ... (imports)

@router.post("/presign-upload")
def presign_upload(
    filename: str = Body(..., embed=True),
    content_type: str = Body("application/octet-stream", embed=True),
    service: ObjectStoreService = Depends(get_service),
    auth: AuthContext = Depends(get_auth_context),
    ctx: RequestContext = Depends(get_request_context),
    gate_chain: GateChain = Depends(get_gate_chain),
) -> Dict[str, Any]:
    """Generate a presigned POST URL for uploading usage content."""
    enforce_tenant_context(ctx, auth)
    
    try:
        gate_chain.run(ctx, action="raw_presign", surface="raw_storage", subject_type="raw_asset")
        return service.presign_upload(ctx, filename, content_type)
    except HTTPException:
        raise
    except Exception as exc:
        return error_response(code="nexus.raw_presign_failed", message=str(exc), status_code=500)


@router.post("/register", response_model=RawAsset)
def register_asset(
    asset: RawAsset,
    service: ObjectStoreService = Depends(get_service),
    auth: AuthContext = Depends(get_auth_context),
    ctx: RequestContext = Depends(get_request_context),
    gate_chain: GateChain = Depends(get_gate_chain),
) -> RawAsset:
    enforce_tenant_context(ctx, auth)
    
    try:
        gate_chain.run(ctx, action="raw_register", surface="raw_storage", subject_type="raw_asset", subject_id=asset.asset_id)
        assert_context_matches(ctx, asset.tenant_id, asset.env)
        return service.register_asset(
            ctx,
            asset.asset_id,
            asset.filename,
            asset.content_type,
            size_bytes=asset.size_bytes,
            metadata=asset.metadata,
        )
    except HTTPException:
        raise
    except Exception as exc:
        return error_response(code="nexus.raw_register_failed", message=str(exc), status_code=500)


@router.post("/put")
async def put_object(
    request: Request,
    key: str = Query(..., description="Object key/path"),
    ctx: RequestContext = Depends(get_request_context),
    gate_chain: GateChain = Depends(get_gate_chain),
) -> Dict[str, Any]:
    """Store a raw binary blob in object store.
    
    - Accepts binary data in request body
    - Backend-class guard enforced: filesystem forbidden in sellable modes
    """
    # Enforce GateChain
    try:
        gate_chain.run(ctx, action="raw_put", surface="raw_storage", subject_type="object", subject_id=key)
    except HTTPException as exc:
        raise exc

    try:
        body = await request.body()
        service = ObjectStoreService()
        service.put(ctx, key, body)
        
        return {
            "key": key,
            "status": "success",
            "message": f"Object stored at {key}",
        }
    
    except ForbiddenBackendClass as e:
        return error_response(code="nexus.backend_forbidden", message=str(e), status_code=403)
    except Exception as e:
        return error_response(code="nexus.raw_put_failed", message=str(e), status_code=500)


@router.get("/get")
async def get_object(
    key: str = Query(..., description="Object key/path"),
    ctx: RequestContext = Depends(get_request_context),
) -> bytes:
    """Retrieve a raw binary blob from object store.
    
    - Returns binary data with appropriate content-type
    - Backend-class guard enforced: filesystem forbidden in sellable modes
    """
    try:
        service = ObjectStoreService()
        data = service.get(ctx, key)
        
        if data is None:
            return error_response(code="nexus.object_not_found", message=f"Object not found: {key}", status_code=404)
        
        return data
    
    except ForbiddenBackendClass as e:
        return error_response(code="nexus.backend_forbidden", message=str(e), status_code=403)
    except HTTPException:
        raise
    except Exception as e:
        return error_response(code="nexus.raw_get_failed", message=str(e), status_code=500)

