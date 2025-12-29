from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException, Depends

from engines.common.identity import RequestContext, get_request_context
from engines.identity.auth import AuthContext, get_auth_context, require_tenant_membership
from engines.audio_service.models import (
    AlignRequest,
    ArtifactRef,
    AsrRequest,
    BeatFeaturesRequest,
    PreprocessRequest,
    SegmentRequest,
    VoiceEnhanceRequest,
)
from engines.audio_service.service import get_audio_service

router = APIRouter(prefix="/audio", tags=["audio_service"])


@router.post("/preprocess", response_model=List[ArtifactRef])
def preprocess(
    req: PreprocessRequest,
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    require_tenant_membership(auth_context, request_context.tenant_id)
    try:
        return get_audio_service().preprocess(req)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/segment", response_model=List[ArtifactRef])
def segment(
    req: SegmentRequest,
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    require_tenant_membership(auth_context, request_context.tenant_id)
    try:
        return get_audio_service().segment(req)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/beat-features", response_model=List[ArtifactRef])
def beat_features(
    req: BeatFeaturesRequest,
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    require_tenant_membership(auth_context, request_context.tenant_id)
    try:
        return get_audio_service().beat_features(req)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/asr", response_model=List[ArtifactRef])
def asr(
    req: AsrRequest,
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    require_tenant_membership(auth_context, request_context.tenant_id)
    try:
        return get_audio_service().asr(req)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/align", response_model=ArtifactRef)
def align(
    req: AlignRequest,
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    require_tenant_membership(auth_context, request_context.tenant_id)
    try:
        return get_audio_service().align(req)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/voice-enhance", response_model=ArtifactRef)
def voice_enhance(
    req: VoiceEnhanceRequest,
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    require_tenant_membership(auth_context, request_context.tenant_id)
    try:
        return get_audio_service().voice_enhance(req)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
