from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from engines.common.error_envelope import error_response
from engines.common.identity import RequestContext, get_request_context
from engines.nexus.hardening.gate_chain import GateChain, get_gate_chain
from engines.audio_semantic_timeline.models import (
    AudioSemanticAnalyzeRequest,
    AudioSemanticAnalyzeResult,
    AudioSemanticTimelineGetResponse,
)
from engines.audio_semantic_timeline.service import get_audio_semantic_service

router = APIRouter(prefix="/audio/semantic-timeline", tags=["audio_semantic_timeline"])


@router.post("/analyze", response_model=AudioSemanticAnalyzeResult)
def analyze_audio_semantic(
    req: AudioSemanticAnalyzeRequest,
    ctx: RequestContext = Depends(get_request_context),
    gate_chain: GateChain = Depends(get_gate_chain),
):
    # Enforce GateChain for mutation/analyze
    try:
        gate_chain.run(ctx=ctx, action="audio_semantic_analyze", resource_kind="audio_timeline")
    except HTTPException as exc:
        raise exc

    try:
        return get_audio_semantic_service().analyze(req)
    except FileNotFoundError as exc:
        return error_response(code="audio.not_found", message=str(exc), status_code=404)
    except Exception as exc:
        return error_response(code="audio.analyze_failed", message=str(exc), status_code=500)


@router.get("/{artifact_id}", response_model=AudioSemanticTimelineGetResponse)
def get_audio_semantic(
    artifact_id: str,
    ctx: RequestContext = Depends(get_request_context),
):
    try:
        return get_audio_semantic_service().get_timeline(artifact_id)
    except FileNotFoundError as exc:
        return error_response(code="audio.timeline_not_found", message=str(exc), status_code=404)
    except Exception as exc:
        return error_response(code="audio.fetch_failed", message=str(exc), status_code=500)


@router.get("/by-clip/{clip_id}", response_model=AudioSemanticTimelineGetResponse)
def get_audio_semantic_by_clip(
    clip_id: str,
    ctx: RequestContext = Depends(get_request_context),
):
    try:
        return get_audio_semantic_service().get_timeline_for_clip(clip_id)
    except FileNotFoundError as exc:
        return error_response(code="audio.clip_lines_not_found", message=str(exc), status_code=404)
    except Exception as exc:
        return error_response(code="audio.fetch_failed", message=str(exc), status_code=500)
