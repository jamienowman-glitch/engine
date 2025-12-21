import subprocess
import json
from typing import Optional, Dict, Any
from engines.media_v2.service import get_media_service, MediaService
from engines.media_integrity.models import IntegrityReport, StreamInfo, IntegrityStatus

class MediaIntegrityService:
    def __init__(self, media_service: Optional[MediaService] = None):
        self.media_service = media_service or get_media_service()

    def _run_ffprobe(self, file_path: str) -> Dict[str, Any]:
        cmd = [
            "ffprobe", 
            "-v", "quiet", 
            "-print_format", "json", 
            "-show_format", 
            "-show_streams", 
            file_path
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return json.loads(result.stdout)
        except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError):
            return {}

    def check_asset(self, asset_id: str) -> Optional[IntegrityReport]:
        asset = self.media_service.get_asset(asset_id)
        if not asset or not asset.source_uri:
            return None
            
        # In a real system, we'd need to handle S3/GCS paths logic here (download to temp).
        # Assuming local path for now as per test environment standard or a mounted path.
        path = asset.source_uri
        
        probe_data = self._run_ffprobe(path)
        
        streams = []
        messages = []
        status: IntegrityStatus = "OK"
        
        if not probe_data:
            status = "CORRUPT"
            messages.append("ffprobe failed or returned empty data")
        else:
            format_data = probe_data.get("format", {})
            if not format_data.get("duration"):
                 # Sometimes duration is in stream, but format usually has it.
                 # Let's check.
                 pass
            
            for s in probe_data.get("streams", []):
                info = StreamInfo(
                    index=s.get("index", 0),
                    codec_type=s.get("codec_type", "unknown"),
                    codec_name=s.get("codec_name", "unknown"),
                    width=s.get("width"),
                    height=s.get("height"),
                    pix_fmt=s.get("pix_fmt"),
                    color_space=s.get("color_space"),
                    duration=float(s.get("duration", 0)) if s.get("duration") else None
                )
                streams.append(info)
                
                # Colour Space Check (Example)
                if info.codec_type == "video":
                    if not info.color_space:
                        messages.append(f"Stream {info.index}: Missing color_space metadata (potential warning)")
                        if status == "OK": status = "WARNING"
                        
        return IntegrityReport(
            asset_id=asset_id,
            status=status,
            streams=streams,
            messages=messages
        )

_svc = None
def get_integrity_service() -> MediaIntegrityService:
    global _svc
    if _svc is None:
        _svc = MediaIntegrityService()
    return _svc
