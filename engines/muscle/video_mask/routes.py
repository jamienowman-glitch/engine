from __future__ import annotations

from fastapi import APIRouter, HTTPException

from engines.video_mask.models import MaskRequest, MaskResult
from engines.video_mask.service import get_mask_service

router = APIRouter(prefix="/video/masks", tags=["video_masks"])


@router.post("/auto", response_model=MaskResult)
def create_mask(req: MaskRequest):
    try:
        return get_mask_service().create_mask(req)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{artifact_id}", response_model=MaskResult)
def get_mask(artifact_id: str):
    svc = get_mask_service()
    art = svc.media_service.get_artifact(artifact_id)
    if not art:
        raise HTTPException(status_code=404, detail="mask artifact not found")
    return MaskResult(artifact_id=art.id, uri=art.uri, meta=art.meta)
