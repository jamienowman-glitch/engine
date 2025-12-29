from fastapi import APIRouter, Depends
from engines.common.identity import RequestContext, get_request_context
from engines.video_anonymise.models import AnonymiseFacesRequest, AnonymiseFacesResult
from engines.video_anonymise.service import get_video_anonymise_service, VideoAnonymiseService

router = APIRouter(prefix="/video/anonymise", tags=["video_anonymise"])


@router.post("/faces", response_model=AnonymiseFacesResult)
def anonymise_faces(
    req: AnonymiseFacesRequest,
    context: RequestContext = Depends(get_request_context),
    service: VideoAnonymiseService = Depends(get_video_anonymise_service),
):
    return service.anonymise_sequence(req, context)
