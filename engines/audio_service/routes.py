from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException

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
def preprocess(req: PreprocessRequest):
    try:
        return get_audio_service().preprocess(req)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/segment", response_model=List[ArtifactRef])
def segment(req: SegmentRequest):
    try:
        return get_audio_service().segment(req)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/beat-features", response_model=List[ArtifactRef])
def beat_features(req: BeatFeaturesRequest):
    try:
        return get_audio_service().beat_features(req)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/asr", response_model=List[ArtifactRef])
def asr(req: AsrRequest):
    try:
        return get_audio_service().asr(req)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/align", response_model=ArtifactRef)
def align(req: AlignRequest):
    try:
        return get_audio_service().align(req)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/voice-enhance", response_model=ArtifactRef)
def voice_enhance(req: VoiceEnhanceRequest):
    try:
        return get_audio_service().voice_enhance(req)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
