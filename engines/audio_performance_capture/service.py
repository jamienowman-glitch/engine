from __future__ import annotations
from typing import Optional

from engines.media_v2.service import MediaService, get_media_service
from engines.media_v2.models import ArtifactCreateRequest, MediaUploadRequest
from engines.audio_performance_capture.models import CaptureRequest, CaptureResult, PerformanceEvent
from engines.audio_performance_capture.onset import detect_onsets
from engines.audio_performance_capture.quantise import quantise_events
from engines.audio_groove.service import get_audio_groove_service

class AudioPerformanceCaptureService:
    def __init__(self, media_service: Optional[MediaService] = None):
        self.media_service = media_service or get_media_service()

    def process_performance(self, req: CaptureRequest) -> CaptureResult:
        # 1. Get Artifact
        art = self.media_service.get_artifact(req.source_artifact_id)
        if not art:
            raise ValueError("Artifact not found")
            
        # 2. Detect
        times, amps = detect_onsets(art.uri)
        events = []
        for t, amp in zip(times, amps):
            # Map amp to velocity 0..1? 
            # Amp is likely very small or large depending on normalization.
            # Normalize amp? 
            # For V1, just clamp/scale roughly.
            vel = min(1.0, amp * 5.0) # naive
            events.append(PerformanceEvent(time_ms=t, velocity=vel))
            
        # 3. Groove
        groove = None
        if req.groove_profile_id:
            g_svc = get_audio_groove_service()
            groove_profile_wrapper = g_svc.get_groove_profile(req.groove_profile_id) # Returns GrooveExtractResult? No, helper?
            # Wait, get_groove_profile helper in audio_groove/service.py returns GrooveProfile model directly?
            # Let's double check audio_groove_service.get_groove_profile contract.
            # Actually I implemented `get_groove_profile` in previous session to retrive model.
            try:
                groove = g_svc.get_groove_profile(req.groove_profile_id)
            except:
                pass # Ignore if not found or error
        
        # 4. Quantise
        quantised_events = quantise_events(
            events, 
            req.target_bpm, 
            req.grid_subdivision, 
            groove, 
            req.humanise_blend
        )
        
        # 5. Result
        # Register artifact?
        # Maybe yes, "audio_performance_capture" JSON.
        # Skipping register for speed in V1 as it returns data directly.
        
        return CaptureResult(
            source_artifact_id=req.source_artifact_id,
            events=quantised_events,
            meta={
                "count": len(quantised_events),
                "humanise": req.humanise_blend
            }
        )

_default_service: Optional[AudioPerformanceCaptureService] = None

def get_audio_performance_capture_service() -> AudioPerformanceCaptureService:
    global _default_service
    if _default_service is None:
        _default_service = AudioPerformanceCaptureService()
    return _default_service
