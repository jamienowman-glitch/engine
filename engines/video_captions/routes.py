from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from engines.common.identity import RequestContext, get_request_context
from engines.video_captions.service import get_captions_service

router = APIRouter()


class GenerateCaptionsRequest(BaseModel):
    asset_id: str
    language: str | None = None


@router.post("/video/captions/generate")
async def generate_captions(
    req: GenerateCaptionsRequest, context: RequestContext = Depends(get_request_context)
):
    svc = get_captions_service()
    try:
        artifact = svc.generate_captions(req.asset_id, language=req.language, context=context)
        return {"status": "success", "artifact_id": artifact.id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/video/captions/{artifact_id}/srt")
async def captions_to_srt(
    artifact_id: str, context: RequestContext = Depends(get_request_context)
):
    svc = get_captions_service()
    try:
        srt_path = svc.convert_to_srt(artifact_id, context=context)
        return {"status": "success", "srt_path": srt_path}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
