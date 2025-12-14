from typing import List, Optional

from fastapi import APIRouter, HTTPException

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
from engines.video_multicam.service import get_multicam_service

router = APIRouter(prefix="/video/multicam", tags=["video_multicam"])


@router.post("/sessions", response_model=MultiCamSession)
def create_session(req: CreateMultiCamSessionRequest):
    service = get_multicam_service()
    try:
        return service.create_session(req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/sessions", response_model=List[MultiCamSession])
def list_sessions(tenant_id: str, project_id: Optional[str] = None):
    service = get_multicam_service()
    return service.list_sessions(tenant_id, project_id=project_id)


@router.get("/sessions/{session_id}", response_model=MultiCamSession)
def get_session(session_id: str):
    service = get_multicam_service()
    session = service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.post("/sessions/{session_id}/align", response_model=MultiCamAlignResult)
def align_session(session_id: str, req: MultiCamAlignRequest):
    if req.session_id != session_id:
        raise HTTPException(status_code=400, detail="Session ID mismatch")
    service = get_multicam_service()
    try:
        return service.align_session(req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/sessions/{session_id}/build-sequence", response_model=MultiCamBuildSequenceResult)
def build_sequence(session_id: str, req: MultiCamBuildSequenceRequest):
    if req.session_id != session_id:
        raise HTTPException(status_code=400, detail="Session ID mismatch")
    service = get_multicam_service()
    try:
        return service.build_sequence(req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/sessions/{session_id}/auto-cut", response_model=MultiCamAutoCutResult)
def auto_cut_session(session_id: str, req: MultiCamAutoCutRequest):
    if req.session_id != session_id:
        raise HTTPException(status_code=400, detail="Session ID mismatch")
    service = get_multicam_service()
    try:
        return service.auto_cut_sequence(req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
