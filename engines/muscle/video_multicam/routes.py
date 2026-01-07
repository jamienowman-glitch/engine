from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException

from engines.common.error_envelope import error_response
from engines.common.identity import RequestContext, get_request_context
from engines.nexus.hardening.gate_chain import GateChain, get_gate_chain
from engines.video_multicam.models import (
    CreateMultiCamSessionRequest,
    MultiCamAlignRequest,
    MultiCamAlignResult,
    MultiCamAutoCutRequest,
    MultiCamAutoCutResult,
    MultiCamBuildSequenceRequest,
    MultiCamBuildSequenceResult,
    MultiCamSession,
)
from engines.video_multicam.service import get_multicam_service, MultiCamService

router = APIRouter(prefix="/video/multicam", tags=["video_multicam"])


def _enforce_gate(gate_chain: GateChain, ctx: RequestContext, action: str):
    try:
        gate_chain.run(ctx=ctx, action=action, resource_kind="video_multicam")
    except HTTPException as exc:
        raise exc


@router.post("/sessions", response_model=MultiCamSession)
def create_session(
    req: CreateMultiCamSessionRequest,
    service: MultiCamService = Depends(get_multicam_service),
    ctx: RequestContext = Depends(get_request_context),
    gate_chain: GateChain = Depends(get_gate_chain),
):
    _enforce_gate(gate_chain, ctx, "video_multicam_create")
    try:
        return service.create_session(req)
    except ValueError as e:
        return error_response(code="multicam.invalid_request", message=str(e), status_code=400)


@router.get("/sessions", response_model=List[MultiCamSession])
def list_sessions(
    project_id: Optional[str] = None,
    service: MultiCamService = Depends(get_multicam_service),
    ctx: RequestContext = Depends(get_request_context),
):
    # Uses Identity context for tenant_id.
    # project_id can be filtered if provided.
    return service.list_sessions(ctx.tenant_id, project_id=project_id)


@router.get("/sessions/{session_id}", response_model=MultiCamSession)
def get_session(
    session_id: str,
    service: MultiCamService = Depends(get_multicam_service),
    ctx: RequestContext = Depends(get_request_context),
):
    session = service.get_session(session_id)
    if not session:
        return error_response(code="multicam.session_not_found", message="Session not found", status_code=404)
    if session.tenant_id != ctx.tenant_id:
        return error_response(code="multicam.access_denied", message="Access denied", status_code=403)
    return session


@router.post("/sessions/{session_id}/align", response_model=MultiCamAlignResult)
def align_session(
    session_id: str,
    req: MultiCamAlignRequest,
    service: MultiCamService = Depends(get_multicam_service),
    ctx: RequestContext = Depends(get_request_context),
    gate_chain: GateChain = Depends(get_gate_chain),
):
    _enforce_gate(gate_chain, ctx, "video_multicam_align")
    if req.session_id != session_id:
        return error_response(code="multicam.id_mismatch", message="Session ID mismatch", status_code=400)
    try:
        return service.align_session(req)
    except ValueError as e:
        return error_response(code="multicam.align_failed", message=str(e), status_code=400)


@router.post("/sessions/{session_id}/build-sequence", response_model=MultiCamBuildSequenceResult)
def build_sequence(
    session_id: str,
    req: MultiCamBuildSequenceRequest,
    service: MultiCamService = Depends(get_multicam_service),
    ctx: RequestContext = Depends(get_request_context),
    gate_chain: GateChain = Depends(get_gate_chain),
):
    _enforce_gate(gate_chain, ctx, "video_multicam_build")
    if req.session_id != session_id:
        return error_response(code="multicam.id_mismatch", message="Session ID mismatch", status_code=400)
    try:
        return service.build_sequence(req)
    except ValueError as e:
        return error_response(code="multicam.build_failed", message=str(e), status_code=400)


@router.post("/sessions/{session_id}/auto-cut", response_model=MultiCamAutoCutResult)
def auto_cut_session(
    session_id: str,
    req: MultiCamAutoCutRequest,
    service: MultiCamService = Depends(get_multicam_service),
    ctx: RequestContext = Depends(get_request_context),
    gate_chain: GateChain = Depends(get_gate_chain),
):
    _enforce_gate(gate_chain, ctx, "video_multicam_autocut")
    if req.session_id != session_id:
        return error_response(code="multicam.id_mismatch", message="Session ID mismatch", status_code=400)
    try:
        return service.auto_cut_sequence(req)
    except ValueError as e:
        return error_response(code="multicam.autocut_failed", message=str(e), status_code=400)
