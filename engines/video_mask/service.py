from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Protocol

from engines.media_v2.models import ArtifactCreateRequest
from engines.media_v2.service import get_media_service
from engines.storage.gcs_client import GcsClient
from engines.video_mask.models import MaskRequest, MaskResult, MaskPrompt


class MaskBackend(Protocol):
    def run(self, video_path: Path, prompt: MaskPrompt, start_ms: int | None, end_ms: int | None, quality: str) -> Path:
        ...


class DummyMaskBackend:
    """Placeholder backend that writes a full-white mask file."""

    def run(self, video_path: Path, prompt: MaskPrompt, start_ms: int | None, end_ms: int | None, quality: str) -> Path:
        dest = Path(tempfile.mkdtemp(prefix="mask_")) / "mask.png"
        dest.write_bytes(b"\xff")
        return dest


class MaskService:
    def __init__(self, backend: MaskBackend | None = None) -> None:
        self.backend = backend or DummyMaskBackend()
        self.media_service = get_media_service()
        try:
            self.gcs = GcsClient()
        except Exception:
            self.gcs = None

    def _download_if_gcs(self, uri: str) -> str:
        if uri.startswith("gs://") and self.gcs:
            tmp_dir = Path(tempfile.mkdtemp(prefix="mask_src_"))
            dest = tmp_dir / Path(uri).name
            try:
                bucket_path = uri.replace("gs://", "", 1)
                bucket_name, key = bucket_path.split("/", 1)
                bucket = self.gcs._client.bucket(bucket_name)  # type: ignore[attr-defined]
                blob = bucket.blob(key)
                blob.download_to_filename(str(dest))
                return str(dest)
            except Exception:
                return uri
        return uri

    def _run_model(self, source_path: str, prompt: MaskPrompt) -> str:
        # STUB: Real implementation would load SAM-2 or FaceParsing model
        # For now, we generate a dummy mask using ffmpeg (white circle/rect on black)
        # to prove the pipeline works.
        
        output_name = f"mask_{uuid.uuid4().hex}.mp4"
        output_path = str(Path(tempfile.gettempdir()) / output_name)
        
        # Simple test pattern mask
        filter_str = "color=black:size=1280x720[base];color=white:size=300x300[patch];[base][patch]overlay=x=490:y=210"
        
        if prompt.prompt_type == "face_region":
             # Different dummy masks for different regions to verify logic
             if prompt.region == "teeth":
                 # Small white box in middle
                 filter_str = "color=black:size=1280x720[base];color=white:size=200x50[patch];[base][patch]overlay=x=540:y=400"
             elif prompt.region == "skin":
                 # Full frame mask except eyes (rough approximation for testing)
                 filter_str = "color=white:size=1280x720[base];color=black:size=1280x100[eyes];[base][eyes]overlay=x=0:y=300"

        # Generate 1 sec mask
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", filter_str,
            "-t", "1",
            "-pix_fmt", "yuv420p", # Ensure compatible format
            output_path
        ]
        
        subprocess.run(cmd, check=True, capture_output=True)
        return output_path

    def _resolve_source(self, req: MaskRequest) -> tuple[Path, str]:
        if req.artifact_id:
            art = self.media_service.get_artifact(req.artifact_id)
            if art:
                return Path(self._download_if_gcs(art.uri)), art.parent_asset_id
        if req.source_asset_id:
            asset = self.media_service.get_asset(req.source_asset_id)
            if asset:
                return Path(self._download_if_gcs(asset.source_uri)), asset.id
        raise FileNotFoundError("source not found")

    def _upload_mask(self, tenant_id: str, asset_id: str, path: Path) -> str:
        if self.gcs:
            try:
                return self.gcs.upload_raw_media(tenant_id, f"{asset_id}/mask/{path.name}", path)
            except Exception:
                return str(path)
        return str(path)

    def create_mask(self, req: MaskRequest) -> MaskResult:
        source_path, parent_asset_id = self._resolve_source(req)
        mask_path = self.backend.run(source_path, req.prompt, req.start_ms, req.end_ms, req.quality)
        uri = self._upload_mask(req.tenant_id, parent_asset_id, mask_path)
        artifact = self.media_service.register_artifact(
            ArtifactCreateRequest(
                tenant_id=req.tenant_id,
                env=req.env,
                parent_asset_id=parent_asset_id or "",
                kind="mask",  # type: ignore[arg-type]
                uri=uri,
                start_ms=req.start_ms,
                end_ms=req.end_ms,
                meta={"backend": self.backend.__class__.__name__, "quality": req.quality},
            )
        )
        return MaskResult(artifact_id=artifact.id, uri=artifact.uri, meta=artifact.meta)


_default_service: MaskService | None = None


def get_mask_service() -> MaskService:
    global _default_service
    if _default_service is None:
        _default_service = MaskService()
    return _default_service


def set_mask_service(service: MaskService) -> None:
    global _default_service
    _default_service = service
