from __future__ import annotations
from typing import Optional

from engines.media_v2.service import MediaService, get_media_service
from engines.audio_harmony.models import HarmonyRequest, HarmonyResult, KeyEstimate
from engines.audio_harmony.detector import estimate_key, NOTES
from engines.audio_resample.service import AudioResampleService, get_audio_resample_service
from engines.audio_resample.models import ResampleRequest

class AudioHarmonyService:
    def __init__(self, media_service: Optional[MediaService] = None, resample_service: Optional[AudioResampleService] = None):
        self.media_service = media_service or get_media_service()
        self.resample_service = resample_service or get_audio_resample_service()

    def detect_key(self, artifact_id: str) -> KeyEstimate:
        art = self.media_service.get_artifact(artifact_id)
        if not art:
            raise ValueError("Artifact not found")
            
        est = estimate_key(art.uri)
        
        # Update Meta
        art.meta["key_root"] = est.root
        art.meta["key_scale"] = est.scale
        art.meta["key_confidence"] = est.confidence
        # We assume media service can update, or we don't save?
        # V1: InMemory backend updates object reference.
        
        return est

    def adapt_to_key(self, req: HarmonyRequest) -> HarmonyResult:
        art = self.media_service.get_artifact(req.artifact_id)
        if not art:
             raise ValueError("Artifact not found")
             
        source_root = art.meta.get("key_root")
        if not source_root:
            # On-the-fly detection
            est = self.detect_key(req.artifact_id)
            source_root = est.root
            
        # Calculate Semitone Shift
        # Map roots to integers 0-11
        try:
            src_idx = NOTES.index(source_root)
            tgt_idx = NOTES.index(req.target_key_root)
        except ValueError:
            # Unknown key? No shift.
            return HarmonyResult(artifact_id=art.id, uri=art.uri, meta={"status": "skipped", "reason": "unknown_key"})
            
        semitones = tgt_idx - src_idx
        
        # Normalize to shortest interval [-6, 6]?
        # e.g. +11 semitones -> -1 semitone
        if semitones > 6:
            semitones -= 12
        elif semitones < -6:
            semitones += 12
            
        if semitones == 0:
             return HarmonyResult(artifact_id=art.id, uri=art.uri, meta={"status": "no_change"})
             
        # Call Resampler
        resample_req = ResampleRequest(
            tenant_id=req.tenant_id,
            env=req.env,
            artifact_id=req.artifact_id,
            pitch_semitones=semitones,
            # Pass BPM to preserve it?
            # If we don't pass target_bpm, rubberband only shifts pitch (which is what we want for pure transposition).
            # But rubberband might default to coupling. 
            # DSP logic check: if pitch is set, rubberband=pitch=... is used.
        )
        
        res_res = self.resample_service.resample_artifact(resample_req)
        
        return HarmonyResult(
            artifact_id=res_res.artifact_id, 
            uri=res_res.uri,
            meta={
                "pitch_shift": semitones, 
                "source_key": source_root, 
                "target_key": req.target_key_root
            }
        )

_default_service: Optional[AudioHarmonyService] = None

def get_audio_harmony_service() -> AudioHarmonyService:
    global _default_service
    if _default_service is None:
        _default_service = AudioHarmonyService()
    return _default_service
