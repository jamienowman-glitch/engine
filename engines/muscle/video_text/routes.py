from fastapi import APIRouter, Depends, HTTPException

from engines.common.error_envelope import error_response
from engines.common.identity import RequestContext, get_request_context
from engines.nexus.hardening.gate_chain import GateChain, get_gate_chain
from engines.video_text.models import TextRenderRequest, TextRenderResponse
from engines.video_text.service import get_video_text_service

router = APIRouter(prefix="/video/text", tags=["video_text"])


@router.post("/render", response_model=TextRenderResponse)
def render_text(
    req: TextRenderRequest,
    ctx: RequestContext = Depends(get_request_context),
    gate_chain: GateChain = Depends(get_gate_chain),
):
    try:
        gate_chain.run(ctx=ctx, action="video_text_render", resource_kind="video_text")
    except HTTPException as exc:
        raise exc

    service = get_video_text_service()
    try:
        return service.render_text_image(req)
    except Exception as e:
        return error_response(code="video_text.render_failed", message=str(e), status_code=400)
