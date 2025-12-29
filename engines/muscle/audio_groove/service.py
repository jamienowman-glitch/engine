from __future__ import annotations
import json
import uuid
import tempfile
from pathlib import Path
from typing import Optional

from engines.media_v2.service import MediaService, get_media_service
from engines.media_v2.models import ArtifactCreateRequest, MediaUploadRequest, DerivedArtifact
from engines.audio_groove.models import GrooveExtractRequest, GrooveExtractResult, GrooveProfile
from engines.audio_groove.dsp import extract_groove_offsets

class AudioGrooveService:
    def __init__(self, media_service: Optional[MediaService] = None):
        self.media_service = media_service or get_media_service()

    def extract_groove(self, req: GrooveExtractRequest) -> GrooveExtractResult:
        # 1. Get Source
        art = self.media_service.get_artifact(req.artifact_id)
        if not art:
            raise ValueError(f"Artifact not found: {req.artifact_id}")
            
        bpm = req.bpm_hint or art.meta.get("bpm")
        if not bpm:
            raise ValueError("BPM required for groove extraction")
            
        # 2. Extract
        offsets = extract_groove_offsets(art.uri, float(bpm), req.subdivision)
        
        profile = GrooveProfile(
            bpm=float(bpm),
            subdivision=len(offsets),
            offsets=offsets
        )
        
        # 3. Register
        manifest_json = profile.json()
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write(manifest_json)
            tmp_path = Path(f.name)
            
        up_req = MediaUploadRequest(
            tenant_id=req.tenant_id, env=req.env, kind="other",
            source_uri="pending", tags=["generated", "groove_profile"]
        )
        
        new_asset = self.media_service.register_upload(up_req, f"groove_{uuid.uuid4().hex[:8]}.json", tmp_path.read_bytes())
        
        new_art = self.media_service.register_artifact(
            ArtifactCreateRequest(
                tenant_id=req.tenant_id,
                env=req.env,
                parent_asset_id=new_asset.id,
                kind="audio_groove_profile",
                uri=new_asset.source_uri,
                meta={
                    "source_artifact_id": req.artifact_id,
                    "bpm": bpm,
                    "avg_offset": sum(offsets)/len(offsets),
                    "subdivision": len(offsets)
                }
            )
        )
        
        if tmp_path.exists():
            tmp_path.unlink()
            
        return GrooveExtractResult(
            artifact_id=new_art.id,
            uri=new_art.uri,
            profile=profile,
            meta=new_art.meta
        )

    def get_groove_profile(self, artifact_id: str) -> Optional[GrooveProfile]:
        # Helper to load and parse profile from artifact
        art = self.media_service.get_artifact(artifact_id)
        if not art: return None
        
        # In V1 local dev, uri is path.
        # In prod, need to download.
        # Assuming local path logic or we read content if smaller?
        # For P8, we assume local access or simulate read.
        # If it's a "audio_groove_profile", the URI points to the JSON file.
        try:
            p = Path(art.uri)
            if p.exists():
                data = json.loads(p.read_text())
                return GrooveProfile(**data)
        except Exception:
            return None
        return None

_default_service: Optional[AudioGrooveService] = None

def get_audio_groove_service() -> AudioGrooveService:
    global _default_service
    if _default_service is None:
        _default_service = AudioGrooveService()
    return _default_service
