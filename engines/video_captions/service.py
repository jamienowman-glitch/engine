import json
import os
import tempfile
import uuid
from pathlib import Path
from typing import Optional, List

from engines.common.identity import RequestContext
from engines.media_v2.service import get_media_service
from engines.media_v2.models import ArtifactCreateRequest, MediaAsset, MediaUploadRequest, DerivedArtifact
from engines.storage.gcs_client import GcsClient
from engines.video_captions.backend import AsrBackend, StubAsrBackend, TranscriptSegment, WhisperLocalBackend

class VideoCaptionsService:
    def __init__(self, backend: Optional[AsrBackend] = None):
        self.media_service = get_media_service()
        try:
            self.gcs = GcsClient()
        except Exception:
            self.gcs = None
        if backend:
            self.backend = backend
        else:
            self.backend = self._load_backend()

    def _load_backend(self) -> AsrBackend:
        backend_type = os.getenv("VIDEO_CAPTIONS_BACKEND", "whisper")
        if backend_type == "stub":
            return StubAsrBackend()
        if backend_type == "whisper":
            model_size = os.getenv("VIDEO_CAPTIONS_MODEL", "tiny")
            device = os.getenv("VIDEO_CAPTIONS_DEVICE", "cpu")
            try:
                return WhisperLocalBackend(model_size=model_size, device=device)
            except Exception:
                return StubAsrBackend()
        return StubAsrBackend()

    def _ensure_local(self, uri: str) -> str:
        if uri.startswith("gs://") and self.gcs:
            tmp_dir = Path(tempfile.mkdtemp(prefix="cap_src_"))
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

    def _cache_key(self, asset: MediaAsset, language: str) -> str:
        backend_version = getattr(self.backend, "backend_version", "asr_unknown")
        duration = int(float(asset.duration_ms or 0.0))
        return f"{asset.id}|{language}|{backend_version}|{duration}"

    def _maybe_cached_artifact(self, asset_id: str, cache_key: str, tenant_id: str, env: str) -> Optional[DerivedArtifact]:
        artifacts = self.media_service.list_artifacts_for_asset(asset_id)
        for art in artifacts:
            if art.kind != "asr_transcript":
                continue
            if art.tenant_id != tenant_id or art.env != env:
                continue
            if art.meta.get("cache_key") != cache_key:
                continue
            return art
        return None

    def _validate_tenant_env(self, asset: MediaAsset, context: Optional[RequestContext]) -> None:
        if not asset.tenant_id or asset.tenant_id == "t_unknown":
            raise ValueError("valid tenant_id is required")
        if not asset.env:
            raise ValueError("env is required")
        if context and (context.tenant_id != asset.tenant_id or context.env != asset.env):
            raise ValueError("tenant/env mismatch with request context")

    def generate_captions(
        self, asset_id: str, language: Optional[str] = None, context: Optional[RequestContext] = None
    ) -> DerivedArtifact:
        asset = self.media_service.get_asset(asset_id)
        if not asset:
            raise ValueError(f"Asset {asset_id} not found")
        self._validate_tenant_env(asset, context)

        requested_backend = os.getenv("VIDEO_CAPTIONS_BACKEND", "whisper")
        actual_language = language or os.getenv("VIDEO_CAPTIONS_LANGUAGE", "en")
        cache_key = self._cache_key(asset, actual_language)
        cached = self._maybe_cached_artifact(asset.id, cache_key, asset.tenant_id, asset.env)
        if cached:
            return cached

        local_src = self._ensure_local(asset.source_uri)
        backend = self.backend
        segments = backend.transcribe(local_src, language=actual_language)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(segments, f)
            json_path = f.name

        remote_uri = json_path
        if self.gcs:
            blob_name = f"captions/{asset.tenant_id}/{asset.id}/{uuid.uuid4().hex}.json"
            remote_uri = self.gcs.upload_raw_media(asset.tenant_id, blob_name, Path(json_path))

        duration_ms = float(asset.duration_ms) if asset.duration_ms is not None else 0.0
        model_used = getattr(backend, "model_used", StubAsrBackend.model_used)
        backend_version = getattr(backend, "backend_version", requested_backend)
        create_req = ArtifactCreateRequest(
            tenant_id=asset.tenant_id,
            env=asset.env,
            parent_asset_id=asset.id,
            kind="asr_transcript",
            uri=remote_uri,
            meta={
                "backend_type": requested_backend,
                "backend_version": backend_version,
                "model_used": model_used,
                "language": actual_language,
                "duration_ms": duration_ms,
                "cache_key": cache_key,
                "segment_count": len(segments),
            },
        )
        return self.media_service.register_artifact(create_req)

    def _format_time(self, seconds: float) -> str:
        # SRT Format: HH:MM:SS,mmm
        ms = int((seconds % 1) * 1000)
        total_seconds = int(seconds)
        s = total_seconds % 60
        m = (total_seconds // 60) % 60
        h = total_seconds // 3600
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    def convert_to_srt(self, artifact_id: str, context: Optional[RequestContext] = None) -> str:
        """
        Downloads transcript artifact and converts to local SRT file path.
        """
        art = self.media_service.get_artifact(artifact_id)
        if not art or art.kind != "asr_transcript":
            raise ValueError("Invalid artifact")
        if context and (art.tenant_id != context.tenant_id or art.env != context.env):
            raise ValueError("tenant/env mismatch with request context")
        
        json_path = self._ensure_local(art.uri)
        with open(json_path, 'r') as f:
            segments: List[TranscriptSegment] = json.load(f)
            
        srt_lines = []
        for idx, seg in enumerate(segments, start=1):
            start_str = self._format_time(seg["start"])
            end_str = self._format_time(seg["end"])
            text = seg["text"]
            srt_lines.append(f"{idx}")
            srt_lines.append(f"{start_str} --> {end_str}")
            srt_lines.append(text)
            srt_lines.append("")
            
        with tempfile.NamedTemporaryFile(mode="w", suffix=".srt", delete=False) as f:
            f.write("\n".join(srt_lines))
            return f.name

_instance: Optional[VideoCaptionsService] = None

def get_captions_service() -> VideoCaptionsService:
    global _instance
    if _instance is None:
        _instance = VideoCaptionsService()
    return _instance
