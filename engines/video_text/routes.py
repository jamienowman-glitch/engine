from fastapi import APIRouter, HTTPException

from engines.video_text.models import TextRenderRequest, TextRenderResponse
from engines.video_text.service import get_video_text_service

router = APIRouter(prefix="/video/text", tags=["video_text"])


@router.post("/render", response_model=TextRenderResponse)
def render_text(req: TextRenderRequest):
    service = get_video_text_service()
    try:
        return service.render_text_image(req)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
