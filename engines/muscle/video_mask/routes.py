from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from engines.common.error_envelope import error_response
from engines.common.identity import RequestContext, get_request_context
from engines.nexus.hardening.gate_chain import GateChain, get_gate_chain
from engines.video_mask.models import MaskRequest, MaskResult
from engines.video_mask.service import get_mask_service

router = APIRouter(prefix="/video/masks", tags=["video_masks"])


@router.post("/auto", response_model=MaskResult)
def create_mask(
    req: MaskRequest,
    ctx: RequestContext = Depends(get_request_context),
    gate_chain: GateChain = Depends(get_gate_chain),
):
    # Enforce GateChain for mutation
    try:
        gate_chain.run(
            ctx=ctx,
            action="video_mask_create",
            resource_kind="video_mask",
        )
    except HTTPException as exc:
        raise exc

    try:
        return get_mask_service().create_mask(req)
    except FileNotFoundError as exc:
        return error_response(
            code="video_mask.not_found",
            message=str(exc),
            status_code=404,
            resource_kind="video_mask",
        )
    except Exception as exc:
        return error_response(
            code="video_mask.creation_failed",
            message=str(exc),
            status_code=500,
            resource_kind="video_mask",
        )


@router.get("/{artifact_id}", response_model=MaskResult)
def get_mask(
    artifact_id: str,
    ctx: RequestContext = Depends(get_request_context),
):
    # Read-only does not strictly need GateChain but must have Identity
    svc = get_mask_service()
    art = svc.media_service.get_artifact(artifact_id)
    if not art:
        return error_response(
            code="video_mask.not_found",
            message="Mask artifact not found",
            status_code=404,
            resource_kind="video_mask",
            details={"artifact_id": artifact_id},
        )
    return MaskResult(artifact_id=art.id, uri=art.uri, meta=art.meta)
