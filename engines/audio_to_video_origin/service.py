from __future__ import annotations
import json
import uuid
import tempfile
from pathlib import Path
from typing import Optional, List, Dict, Tuple, Any

from engines.media_v2.service import MediaService, get_media_service
from engines.media_v2.models import ArtifactCreateRequest, MediaUploadRequest
from engines.audio_semantic_timeline.models import AudioSemanticTimelineSummary
from engines.audio_semantic_timeline.service import get_audio_semantic_service
from engines.audio_to_video_origin.models import ShotListRequest, ShotListResult, VideoShot, OriginMap

class AudioToVideoOriginService:
    def __init__(self, media_service: Optional[MediaService] = None):
        self.media_service = media_service or get_media_service()
        self.semantic_service = get_audio_semantic_service()
        self._semantic_cache: Dict[str, Tuple[Optional[AudioSemanticTimelineSummary], Dict[str, Any]]] = {}

    def _get_semantic_summary(
        self, asset_id: str
    ) -> Optional[Tuple[AudioSemanticTimelineSummary, Dict[str, Any]]]:
        if asset_id in self._semantic_cache:
            cached = self._semantic_cache[asset_id]
            if cached[0] is None:
                return None
            return cached

        for art in self.media_service.list_artifacts_for_asset(asset_id):
            if art.kind == "audio_semantic_timeline":
                try:
                    resp = self.semantic_service.get_timeline(art.id)
                    summary = resp.summary
                    self._semantic_cache[asset_id] = (summary, art.meta or {})
                    return self._semantic_cache[asset_id]
                except FileNotFoundError:
                    continue
        self._semantic_cache[asset_id] = (None, {})
        return None

    def generate_shot_list(self, req: ShotListRequest) -> ShotListResult:
        shots: List[VideoShot] = []
        semantic_global_meta: Dict[str, Any] = {}
        
        # Iterate all clips in all tracks
        for track in req.sequence.tracks:
            for clip in track.clips:
                # Resolve Artifact
                # If clip has artifact_id, get meta.
                # If asset_id, it might be raw asset -> origin is asset itself, start 0?
                
                source_asset_id = None
                base_source_start_ms = 0.0
                origin_meta: Dict[str, Any] = {}
                
                if clip.artifact_id:
                    art = self.media_service.get_artifact(clip.artifact_id)
                    if art:
                        # Try to find origin info in meta
                        # Ideally populated by field_to_samples
                        # e.g. meta={"source_asset_id": "...", "source_start_ms": 1234}
                        source_asset_id = art.meta.get("source_asset_id")
                        base_source_start_ms = art.meta.get("source_start_ms", 0.0)
                        origin_meta = dict(art.meta)
                        
                        # Fallback: if parent_asset_id is the source video?
                        if not source_asset_id and art.parent_asset_id:
                            # Verify if parent is video? 
                            # For simplified V1, assume parent is source if not in meta.
                            source_asset_id = art.parent_asset_id
                            
                elif clip.asset_id:
                    # Raw asset usage
                    source_asset_id = clip.asset_id
                    base_source_start_ms = 0.0
                    origin_meta = {}
                
                if not source_asset_id:
                    continue # Cannot map to video without source
                    
                semantic_entry = self._get_semantic_summary(source_asset_id)
                semantic_offset = 0.0
                semantic_meta: Dict[str, Any] = {}
                if semantic_entry:
                    summary, meta = semantic_entry
                    semantic_meta = meta
                    if meta:
                        semantic_global_meta = meta
                    speech_events = [ev for ev in summary.events if ev.kind == "speech"]
                    if speech_events:
                        semantic_offset = speech_events[0].start_ms
                valid_source_start = base_source_start_ms + clip.source_offset_ms + semantic_offset
                
                # Calculate Shot Times
                valid_source_end = valid_source_start + clip.duration_ms
                
                shot_meta = {
                    "track": track.name,
                    "role": track.meta.get("role"),
                    **origin_meta,
                    "semantic_version": semantic_meta.get("semantic_version"),
                    "semantic_offset_ms": semantic_offset,
                    "semantic_cache_key": semantic_meta.get("audio_semantic_cache_key"),
                }
                shots.append(VideoShot(
                    source_asset_id=source_asset_id,
                    source_start_ms=valid_source_start,
                    source_end_ms=valid_source_end,
                    target_start_ms=clip.start_ms,
                    target_duration_ms=clip.duration_ms,
                    meta=shot_meta
                ))
        
        # Sort by time
        shots.sort(key=lambda s: s.target_start_ms)
        
        # Register Shot List Artifact?
        # Plan said "Output Output a data-only structure VideoShotList".
        # We can also register it as a JSON artifact for persistence.
        
        manifest_json = json.dumps([s.model_dump() for s in shots], indent=2)
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write(manifest_json)
            tmp_path = Path(f.name)
            
        up_req = MediaUploadRequest(
            tenant_id=req.tenant_id, env=req.env, kind="other",
            source_uri="pending", tags=["generated", "video_shot_list"]
        )
        new_asset = self.media_service.register_upload(up_req, f"shotlist_{uuid.uuid4().hex[:8]}.json", tmp_path.read_bytes())
        
        self.media_service.register_artifact(
            ArtifactCreateRequest(
                tenant_id=req.tenant_id,
                env=req.env,
                parent_asset_id=new_asset.id,
                kind="video_shot_list",
                uri=new_asset.source_uri,
                meta={"shot_count": len(shots)}
            )
        )
        
        if tmp_path.exists():
            tmp_path.unlink()
            
        result_meta: Dict[str, Any] = {"count": len(shots)}
        if semantic_global_meta:
            result_meta["semantic_cache_key"] = semantic_global_meta.get("audio_semantic_cache_key")
            result_meta["semantic_version"] = semantic_global_meta.get("semantic_version")
        return ShotListResult(shots=shots, meta=result_meta)

_default_service: Optional[AudioToVideoOriginService] = None

def get_audio_to_video_origin_service() -> AudioToVideoOriginService:
    global _default_service
    if _default_service is None:
        _default_service = AudioToVideoOriginService()
    return _default_service
