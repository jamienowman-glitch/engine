from fastapi import APIRouter, Depends, HTTPException

from engines.common.error_envelope import error_response
from engines.common.identity import RequestContext, get_request_context
from engines.nexus.hardening.gate_chain import GateChain, get_gate_chain
from engines.video_presets.models import FilterPreset, MotionPreset
from engines.video_presets.service import get_preset_service

router = APIRouter(prefix="/video/presets", tags=["video_presets"])


def _enforce_gate(gate_chain: GateChain, ctx: RequestContext, action: str):
    try:
        gate_chain.run(ctx=ctx, action=action, resource_kind="video_preset")
    except HTTPException as exc:
        raise exc


@router.post("/filters", response_model=FilterPreset)
def create_filter_preset(
    preset: FilterPreset,
    ctx: RequestContext = Depends(get_request_context),
    gate_chain: GateChain = Depends(get_gate_chain),
):
    _enforce_gate(gate_chain, ctx, "video_preset_create_filter")
    return get_preset_service().create_filter_preset(preset)


@router.get("/filters", response_model=list[FilterPreset])
def list_filter_presets(
    tag: str | None = None,
    ctx: RequestContext = Depends(get_request_context),
):
    # Uses identity for tenant/env
    return get_preset_service().list_filter_presets(
        tenant_id=ctx.tenant_id,
        env=ctx.env,
        tag=tag,
    )


@router.get("/filters/{preset_id}", response_model=FilterPreset)
def get_filter_preset(
    preset_id: str,
    ctx: RequestContext = Depends(get_request_context),
):
    preset = get_preset_service().get_filter_preset(preset_id)
    if not preset:
        return error_response(code="preset.not_found", message="Filter preset not found", status_code=404)
    # Validate tenancy
    if preset.tenant_id != ctx.tenant_id:
         return error_response(code="preset.access_denied", message="Access denied", status_code=403)
    return preset


@router.delete("/filters/{preset_id}")
def delete_filter_preset(
    preset_id: str,
    ctx: RequestContext = Depends(get_request_context),
    gate_chain: GateChain = Depends(get_gate_chain),
):
    _enforce_gate(gate_chain, ctx, "video_preset_delete_filter")
    get_preset_service().delete_filter_preset(preset_id)
    return {"status": "deleted", "id": preset_id}


@router.post("/motion", response_model=MotionPreset)
def create_motion_preset(
    preset: MotionPreset,
    ctx: RequestContext = Depends(get_request_context),
    gate_chain: GateChain = Depends(get_gate_chain),
):
    _enforce_gate(gate_chain, ctx, "video_preset_create_motion")
    return get_preset_service().create_motion_preset(preset)


@router.get("/motion", response_model=list[MotionPreset])
def list_motion_presets(
    tag: str | None = None,
    ctx: RequestContext = Depends(get_request_context),
):
    return get_preset_service().list_motion_presets(
        tenant_id=ctx.tenant_id,
        env=ctx.env,
        tag=tag,
    )


@router.get("/motion/{preset_id}", response_model=MotionPreset)
def get_motion_preset(
    preset_id: str,
    ctx: RequestContext = Depends(get_request_context),
):
    preset = get_preset_service().get_motion_preset(preset_id)
    if not preset:
         return error_response(code="preset.not_found", message="Motion preset not found", status_code=404)
    if preset.tenant_id != ctx.tenant_id:
         return error_response(code="preset.access_denied", message="Access denied", status_code=403)
    return preset


@router.delete("/motion/{preset_id}")
def delete_motion_preset(
    preset_id: str,
    ctx: RequestContext = Depends(get_request_context),
    gate_chain: GateChain = Depends(get_gate_chain),
):
    _enforce_gate(gate_chain, ctx, "video_preset_delete_motion")
    get_preset_service().delete_motion_preset(preset_id)
    return {"status": "deleted", "id": preset_id}
