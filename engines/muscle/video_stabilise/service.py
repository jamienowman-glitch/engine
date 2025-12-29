import os
import tempfile
import uuid
from typing import Optional
from pathlib import Path

from engines.media_v2.service import get_media_service
from engines.media_v2.models import ArtifactCreateRequest, MediaUploadRequest, DerivedArtifact
from engines.storage.gcs_client import GcsClient
from engines.video_stabilise.backend import VideoStabiliseBackend, FfmpegStabiliseBackend, StubStabiliseBackend

class VideoStabiliseService:
    def __init__(self, backend: Optional[VideoStabiliseBackend] = None):
        self.media_service = get_media_service()
        try:
            self.gcs = GcsClient()
        except Exception:
            self.gcs = None
        
        if backend:
            self.backend = backend
        else:
            # Use real backend if ffmpeg present, else stub?
            # Or just default to Ffmpeg
            self.backend = FfmpegStabiliseBackend()

    def _ensure_local(self, uri: str) -> str:
        if uri.startswith("gs://") and self.gcs:
            tmp_dir = Path(tempfile.mkdtemp(prefix="stab_src_"))
            dest = tmp_dir / Path(uri).name
            try:
                bucket_path = uri.replace("gs://", "", 1)
                bucket_name, key = bucket_path.split("/", 1)
                bucket = self.gcs._client.bucket(bucket_name) # type: ignore
                blob = bucket.blob(key)
                blob.download_to_filename(str(dest))
                return str(dest)
            except Exception:
                return uri
        return uri

    def analyze(self, asset_id: str) -> Optional[DerivedArtifact]:
        """
        Run stabilisation analysis (pass 1) on the asset.
        Returns the transform artifact.
        """
        # Check existing
        existing = self.media_service.list_artifacts_for_asset(asset_id)
        for art in existing:
            if art.kind == "video_stabilise_transform":
                return art
        
        asset = self.media_service.get_asset(asset_id)
        if not asset:
            raise ValueError(f"Asset {asset_id} not found")
        
        local_src = self._ensure_local(asset.source_uri)
        
        # Generate TRF
        with tempfile.TemporaryDirectory() as tmp_dir:
            trf_path = os.path.join(tmp_dir, "transform.trf")
            self.backend.detect_stability(local_src, trf_path)
            
            if not os.path.exists(trf_path):
                raise RuntimeError("Backend failed to produce transform file")
                
            # Upload
            remote_uri = trf_path
            if self.gcs:
                # Upload to GCS
                blob_name = f"stabilise/{asset.tenant_id}/{asset.id}/{uuid.uuid4().hex}.trf"
                remote_uri = self.gcs.upload_raw_media(
                    asset.tenant_id, 
                    blob_name, 
                    Path(trf_path)
                )

            # Register
            create_req = ArtifactCreateRequest(
                tenant_id=asset.tenant_id,
                env=asset.env,
                parent_asset_id=asset.id,
                kind="video_stabilise_transform",
                uri=remote_uri,
                meta={"backend": "vidstab"}
            )
            return self.media_service.register_artifact(create_req)

_service_instance = None

def get_stabilise_service() -> VideoStabiliseService:
    global _service_instance
    if _service_instance is None:
        _service_instance = VideoStabiliseService()
    return _service_instance
