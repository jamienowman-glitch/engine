from __future__ import annotations

from fastapi import APIRouter, HTTPException

from engines.audio_voice_enhance.models import VoiceEnhanceRequest, VoiceEnhanceResult
from engines.audio_voice_enhance.service import get_voice_enhance_service

router = APIRouter(prefix="/audio/voice-enhance", tags=["audio_voice_enhance"])


@router.post("", response_model=VoiceEnhanceResult)
def enhance(req: VoiceEnhanceRequest):
    try:
        return get_voice_enhance_service().enhance(req)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{artifact_id}", response_model=VoiceEnhanceResult)
def get_artifact(artifact_id: str):
    try:
        return get_voice_enhance_service().get_artifact(artifact_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
