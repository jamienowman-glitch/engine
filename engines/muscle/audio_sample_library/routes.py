from typing import Optional, List

from fastapi import APIRouter, Depends, Query, Path

from engines.audio_sample_library.models import SampleLibraryResult, SampleLibraryQuery, SampleType
from engines.audio_sample_library.service import AudioSampleLibraryService, get_audio_sample_library_service

router = APIRouter(prefix="/audio/sample-library", tags=["audio_sample_library"])

@router.get("/samples", response_model=SampleLibraryResult)
def get_samples(
    tenant_id: str,
    env: str,
    user_id: Optional[str] = None,
    parent_asset_id: Optional[str] = None,
    kind: Optional[SampleType] = None,
    kinds: Optional[List[SampleType]] = Query(None),
    min_bpm: Optional[float] = None,
    max_bpm: Optional[float] = None,
    loop_bars: Optional[int] = None,
    has_transcript: bool = False,
    limit: int = 50,
    offset: int = 0,
    service: AudioSampleLibraryService = Depends(get_audio_sample_library_service)
):
    query = SampleLibraryQuery(
        tenant_id=tenant_id,
        env=env,
        user_id=user_id,
        parent_asset_id=parent_asset_id,
        kind=kind,
        kinds=kinds,
        min_bpm=min_bpm,
        max_bpm=max_bpm,
        loop_bars=loop_bars,
        has_transcript=has_transcript,
        limit=limit,
        offset=offset
    )
    return service.query_samples(query)
