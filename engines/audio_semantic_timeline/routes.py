from __future__ import annotations

from fastapi import APIRouter, HTTPException

from engines.audio_semantic_timeline.models import (
    AudioSemanticAnalyzeRequest,
    AudioSemanticAnalyzeResult,
    AudioSemanticTimelineGetResponse,
)
from engines.audio_semantic_timeline.service import get_audio_semantic_service

router = APIRouter(prefix="/audio/semantic-timeline", tags=["audio_semantic_timeline"])


@router.post("/analyze", response_model=AudioSemanticAnalyzeResult)
def analyze_audio_semantic(req: AudioSemanticAnalyzeRequest):
    try:
        return get_audio_semantic_service().analyze(req)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{artifact_id}", response_model=AudioSemanticTimelineGetResponse)
def get_audio_semantic(artifact_id: str):
    try:
        return get_audio_semantic_service().get_timeline(artifact_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/by-clip/{clip_id}", response_model=AudioSemanticTimelineGetResponse)
def get_audio_semantic_by_clip(clip_id: str):
    try:
        return get_audio_semantic_service().get_timeline_for_clip(clip_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
