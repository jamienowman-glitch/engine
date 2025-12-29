from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from engines.common.identity import RequestContext, get_request_context
from engines.video_visual_meta.models import (
    ReframeSuggestion,
    ReframeSuggestionRequest,
    VisualMetaAnalyzeRequest,
    VisualMetaAnalyzeResult,
    VisualMetaGetResponse,
)
from engines.video_visual_meta.service import get_visual_meta_service

router = APIRouter(prefix="/video/visual-meta", tags=["video_visual_meta"])


@router.post("/analyze", response_model=VisualMetaAnalyzeResult)
async def analyze_visual_meta(
    req: VisualMetaAnalyzeRequest, context: RequestContext = Depends(get_request_context)
):
    try:
        return get_visual_meta_service().analyze(req, context)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{artifact_id}", response_model=VisualMetaGetResponse)
async def get_visual_meta(
    artifact_id: str, context: RequestContext = Depends(get_request_context)
):
    try:
        return get_visual_meta_service().get_visual_meta(artifact_id, context)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/by-clip/{clip_id}", response_model=VisualMetaGetResponse)
async def get_visual_meta_by_clip(
    clip_id: str, context: RequestContext = Depends(get_request_context)
):
    try:
        return get_visual_meta_service().get_visual_meta_for_clip(clip_id, context)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/reframe-suggestion", response_model=ReframeSuggestion)
async def suggest_reframe(
    req: ReframeSuggestionRequest, context: RequestContext = Depends(get_request_context)
):
    try:
        return get_visual_meta_service().suggest_reframe(req)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
