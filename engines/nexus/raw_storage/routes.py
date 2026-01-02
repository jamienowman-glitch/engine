"""Raw Storage API Routes (PHASE_02 enforcement: RequestContext + AuthContext)."""
from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, Body

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

router = APIRouter(prefix="/nexus/raw", tags=["nexus_raw_storage"])


def get_service() -> ObjectStoreService:
    """Get ObjectStoreService with routing-based backend resolution."""
    return ObjectStoreService()


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
    gate_chain.run(ctx, action="raw_presign", surface="raw_storage", subject_type="raw_asset")
    return service.presign_upload(ctx, filename, content_type)


@router.post("/register", response_model=RawAsset)
def register_asset(
    asset: RawAsset,
    service: ObjectStoreService = Depends(get_service),
    auth: AuthContext = Depends(get_auth_context),
    ctx: RequestContext = Depends(get_request_context),
    gate_chain: GateChain = Depends(get_gate_chain),
) -> RawAsset:
    enforce_tenant_context(ctx, auth)
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
