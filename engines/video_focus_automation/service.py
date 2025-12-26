import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from engines.media_v2.service import get_media_service, MediaService
from engines.media_v2.models import DerivedArtifact
from engines.video_timeline.models import ParameterAutomation, Keyframe
from engines.video_focus_automation.models import FocusRequest, FocusResult
from engines.storage.gcs_client import GcsClient

logger = logging.getLogger(__name__)

class FocusAutomationService:
    def __init__(self, media_service: Optional[MediaService] = None):
        self.media_service = media_service or get_media_service()
        self._focus_cache: Dict[str, dict] = {}
        try:
            self.gcs = GcsClient()
        except Exception:
            self.gcs = None

    def _load_artifact_json(self, artifact_id: str) -> Optional[dict]:
        if artifact_id in self._focus_cache:
            return self._focus_cache[artifact_id]
        art = self.media_service.get_artifact(artifact_id)
        if not art:
            return None
        payload = self._artifact_payload(art)
        if payload:
            self._focus_cache[artifact_id] = payload
            return payload
        data = self._load_artifact_content(art)
        if data:
            self._focus_cache[artifact_id] = data
        return data

    def _load_artifact_content(self, art: DerivedArtifact) -> Optional[dict]:
        uri = art.uri
        local_path = uri
        
        # Check if local file exists first (common in tests)
        if os.path.exists(uri):
            try:
                with open(uri, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
                
        if uri.startswith("gs://") and self.gcs:
            # Download temp
            try:
                # We can't rely on tempfile.NamedTemporaryFile delete=False without cleanup
                # But for this V1 script we'll rely on OS temp cleanup or try-finally block.
                # Actually, let's just use a predictable path or read directly? 
                # GCS blob.download_to_filename is standard.
                
                # Ideally cache this?
                # For now: simple temp.
                fd, tmp_path = tempfile.mkstemp(suffix=".json")
                os.close(fd)
                
                bucket_path = uri.replace("gs://", "", 1)
                bucket_name, key = bucket_path.split("/", 1)
                bucket = self.gcs._client.bucket(bucket_name) # type: ignore
                blob = bucket.blob(key)
                blob.download_to_filename(tmp_path)
                
                with open(tmp_path, 'r') as f:
                    data = json.load(f)
                
                os.unlink(tmp_path)
                return data
            except Exception as e:
                print(f"Error reading GCS {uri}: {e}")
                return None
                
        return None

    def _artifact_payload(self, art: DerivedArtifact) -> Optional[dict]:
        payload = art.meta.get("payload")
        if isinstance(payload, dict):
            return payload
        if art.meta:
            meta_keys = set(art.meta.keys())
            if {"events", "frames"} & meta_keys:
                return art.meta
        return None

    def _create_center_fallback(self, req: FocusRequest, asset: Any) -> FocusResult:
        # Default to 0.5, 0.5 static
        kfs_x = [Keyframe(time_ms=0, value=0.5)]
        kfs_y = [Keyframe(time_ms=0, value=0.5)]
        logger.info("Focus fallback to center for clip %s", req.clip_id)
        
        return FocusResult(
            clip_id=req.clip_id,
            automation_x=ParameterAutomation(
                tenant_id=asset.tenant_id, env=asset.env, target_type="clip", target_id=req.clip_id, property="crop_x", keyframes=kfs_x
            ),
            automation_y=ParameterAutomation(
                tenant_id=asset.tenant_id, env=asset.env, target_type="clip", target_id=req.clip_id, property="crop_y", keyframes=kfs_y
            )
        )

    def calculate_focus(self, req: FocusRequest) -> Optional[FocusResult]:
        # Fetch Asset context
        asset = self.media_service.get_asset(req.asset_id)
        if not asset:
            logger.warning("Asset %s not found", req.asset_id)
            return None
            
        # Enforce Tenant/Env from Request if present (assuming req has it, model check needed)
        # Detailed V04 spec says: "rejects tenant/env mismatch"
        # Focusing on asset tenant/env matching request context
        if req.tenant_id and asset.tenant_id != req.tenant_id:
             raise ValueError(f"Access Denied: Asset tenant {asset.tenant_id} != Req {req.tenant_id}")
        if req.env and asset.env != req.env:
             raise ValueError(f"Access Denied: Asset env {asset.env} != Req {req.env}")

        # 1. Resolve Artifacts
        audio_art_id = req.audio_artifact_id
        visual_art_id = req.visual_artifact_id
        
        if not audio_art_id or not visual_art_id:
            # Discovery fallback
            artifacts = self.media_service.list_artifacts_for_asset(req.asset_id)
            for art in artifacts:
                if not audio_art_id and art.kind == "audio_semantic_timeline":
                    audio_art_id = art.id
                elif not visual_art_id and (art.kind == "visual_meta" or art.kind == "video_visual_meta"):
                    visual_art_id = art.id
                    
        if not audio_art_id or not visual_art_id:
            # Missing inputs - Fallback to Center
            logger.info("Focus inputs missing for clip %s, falling back to center", req.clip_id)
            return self._create_center_fallback(req, asset)
            
        audio_data = self._load_artifact_json(audio_art_id)
        visual_data = self._load_artifact_json(visual_art_id)
        
        if not audio_data or not visual_data:
            logger.info("Focus artifact content missing for clip %s, falling back to center", req.clip_id)
            return self._create_center_fallback(req, asset)
            
        # 2. Logic: Generate Curves
        kfs_x = []
        kfs_y = []
        
        v_frames = sorted(visual_data.get("frames", []), key=lambda x: x["timestamp_ms"])
        
        def get_avg_center(start, end):
            xs = []
            ys = []
            for f in v_frames:
                t = f["timestamp_ms"]
                if t >= start and t <= end:
                    cx = f.get("primary_subject_center_x")
                    cy = f.get("primary_subject_center_y")
                    
                    if cx is None and "regions" in f:
                         faces = [r for r in f["regions"] if r.get("label") == "face"]
                         # Also support 'person'
                         if not faces:
                             faces = [r for r in f["regions"] if r.get("label") == "person"]
                             
                         if faces:
                             r = faces[0]
                             cx = r.get("x", 0) + r.get("w", 0)/2
                             cy = r.get("y", 0) + r.get("h", 0)/2
                             
                    if cx is not None: xs.append(cx)
                    if cy is not None: ys.append(cy)
                if t > end:
                    break
            if not xs: return 0.5, 0.5
            return sum(xs)/len(xs), sum(ys)/len(ys)

        events = audio_data.get("events", [])
        
        # Base keyframes
        kfs_x.append(Keyframe(time_ms=0, value=0.5, interpolation="linear"))
        kfs_y.append(Keyframe(time_ms=0, value=0.5, interpolation="linear"))
        
        for evt in events:
            if evt.get("kind") == "speech":
                start = evt.get("start_ms", 0)
                end = evt.get("end_ms", 0)
                if end <= start: continue
                
                cx, cy = get_avg_center(start, end)
                
                # Add hold keyframes
                kfs_x.append(Keyframe(time_ms=start, value=cx, interpolation="linear"))
                kfs_x.append(Keyframe(time_ms=end, value=cx, interpolation="linear"))
                kfs_y.append(Keyframe(time_ms=start, value=cy, interpolation="linear"))
                kfs_y.append(Keyframe(time_ms=end, value=cy, interpolation="linear"))
                
        kfs_x.sort(key=lambda k: k.time_ms)
        kfs_y.sort(key=lambda k: k.time_ms)
        
        result_meta = {
            "automation_version": "v1",
            "source_audio_artifact": audio_art_id,
            "source_visual_artifact": visual_art_id,
        }
        
        return FocusResult(
            clip_id=req.clip_id,
            automation_x=ParameterAutomation(
                tenant_id=asset.tenant_id, env=asset.env, target_type="clip", target_id=req.clip_id, property="crop_x", keyframes=kfs_x
            ),
            automation_y=ParameterAutomation(
                tenant_id=asset.tenant_id, env=asset.env, target_type="clip", target_id=req.clip_id, property="crop_y", keyframes=kfs_y
            ),
            meta=result_meta
        )

_svc = None
def get_focus_service() -> FocusAutomationService:
    global _svc
    if _svc is None:
        _svc = FocusAutomationService()
    return _svc
