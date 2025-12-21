from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Protocol

from engines.audio_voice_enhance.models import VoiceEnhanceMode, VoiceEnhanceRequest, VoiceEnhanceResult
from engines.media_v2.models import ArtifactCreateRequest, DerivedArtifact, MediaAsset
from engines.media_v2.service import get_media_service
from engines.storage.gcs_client import GcsClient


class VoiceEnhanceBackend(Protocol):
    def run(self, audio_path: Path, mode: VoiceEnhanceMode, aggressiveness: float, preserve_ambience: bool) -> Path:
        ...


class FfmpegVoiceEnhanceBackend:
    backend_version = "voice_enhance_ffmpeg_stub_v1"
    model_used = backend_version

    def _filters(self, mode: VoiceEnhanceMode, aggressiveness: float, preserve_ambience: bool) -> list[str]:
        hp = 120
        lp = 12000 if preserve_ambience else 8000
        presence = 3 + int(aggressiveness * 3)
        comp = 6 + int(aggressiveness * 4)
        if mode == "phone_recording":
            hp = 200
            lp = 6000
        if mode == "podcast":
            presence += 1
            comp += 2
        if mode == "vlog":
            lp += 2000
        return [
            f"highpass=f={hp}",
            f"lowpass=f={lp}",
            f"acompressor=threshold=-18dB:ratio=2:makeup={comp}",
            f"anequalizer=f=3500:t=q:w=1.0:g={presence}",
            "afftdn=nf=-25",
        ]

    def run(self, audio_path: Path, mode: VoiceEnhanceMode, aggressiveness: float, preserve_ambience: bool) -> Path:
        out_path = Path(tempfile.mkdtemp(prefix="voice_enh_")) / f"{audio_path.stem}_enhanced.wav"
        if shutil.which("ffmpeg") is None:
            shutil.copy(audio_path, out_path)
            return out_path
        filters = ",".join(self._filters(mode, aggressiveness, preserve_ambience))
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(audio_path),
            "-af",
            filters,
            str(out_path),
        ]
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
        except Exception:
            shutil.copy(audio_path, out_path)
        return out_path


class VoiceEnhanceService:
    def __init__(self, backend: Optional[VoiceEnhanceBackend] = None) -> None:
        self.backend = backend or FfmpegVoiceEnhanceBackend()
        self.media_service = get_media_service()
        try:
            self.gcs = GcsClient()
        except Exception:
            self.gcs = None

    def _cache_key(self, req: VoiceEnhanceRequest, asset_id: str) -> str:
        backend_version = getattr(self.backend, "backend_version", getattr(self.backend, "model_used", "voice_enhance_stub"))
        return f"{asset_id}|{req.artifact_id or 'None'}|{req.mode}|{req.aggressiveness:.3f}|{req.preserve_ambience}|{backend_version}"

    def _maybe_cached(self, asset_id: str, cache_key: str) -> Optional[DerivedArtifact]:
        for art in self.media_service.list_artifacts_for_asset(asset_id):
            if art.kind == "audio_voice_enhanced" and art.meta.get("voice_enhance_cache_key") == cache_key:
                return art
        return None

    def _download_if_gcs(self, uri: str) -> str:
        if uri.startswith("gs://") and self.gcs:
            tmp_path = Path(tempfile.mkdtemp(prefix="voice_enh_src_")) / Path(uri).name
            try:
                bucket_path = uri.replace("gs://", "", 1)
                bucket_name, key = bucket_path.split("/", 1)
                bucket = self.gcs._client.bucket(bucket_name)  # type: ignore[attr-defined]
                blob = bucket.blob(key)
                blob.download_to_filename(str(tmp_path))
                return str(tmp_path)
            except Exception:
                return uri
        return uri

    def _resolve_source(self, req: VoiceEnhanceRequest) -> tuple[MediaAsset, Path]:
        if req.artifact_id:
            art = self.media_service.get_artifact(req.artifact_id)
            if art:
                asset = self.media_service.get_asset(art.parent_asset_id)
                if asset:
                    return asset, Path(self._download_if_gcs(art.uri))
        asset = self.media_service.get_asset(req.asset_id)
        if asset:
            return asset, Path(self._download_if_gcs(asset.source_uri))
        raise FileNotFoundError("source audio not found")

    def _register_artifact(self, req: VoiceEnhanceRequest, asset: MediaAsset, path: Path) -> DerivedArtifact:
        uri = str(path)
        if self.gcs:
            try:
                uri = self.gcs.upload_raw_media(req.tenant_id, f"{asset.id}/voice_enhanced/{path.name}", path)
            except Exception:
                uri = str(path)
        backend_version = getattr(self.backend, "backend_version", getattr(self.backend, "model_used", "voice_enhance_stub"))
        meta = {
            "mode": req.mode,
            "aggressiveness": req.aggressiveness,
            "preserve_ambience": req.preserve_ambience,
            "model_used": getattr(self.backend, "model_used", backend_version),
            "backend_version": backend_version,
            "voice_enhance_cache_key": self._cache_key(req, asset.id),
        }
        if req.target_speaker_id:
            meta["target_speaker_id"] = req.target_speaker_id
        return self.media_service.register_artifact(
            ArtifactCreateRequest(
                tenant_id=req.tenant_id,
                env=req.env,
                parent_asset_id=asset.id,
                kind="audio_voice_enhanced",  # type: ignore[arg-type]
                uri=uri,
                meta=meta,
            )
        )

    def enhance(self, req: VoiceEnhanceRequest) -> VoiceEnhanceResult:
        asset, source_path = self._resolve_source(req)
        cache_key = self._cache_key(req, asset.id)
        cached = self._maybe_cached(asset.id, cache_key)
        if cached:
            return VoiceEnhanceResult(artifact_id=cached.id, uri=cached.uri, meta=cached.meta)
        out_path = self.backend.run(source_path, req.mode, req.aggressiveness, req.preserve_ambience)
        artifact = self._register_artifact(req, asset, out_path)
        return VoiceEnhanceResult(artifact_id=artifact.id, uri=artifact.uri, meta=artifact.meta)

    def get_artifact(self, artifact_id: str) -> VoiceEnhanceResult:
        art = self.media_service.get_artifact(artifact_id)
        if not art:
            raise FileNotFoundError("voice enhanced artifact not found")
        return VoiceEnhanceResult(artifact_id=art.id, uri=art.uri, meta=art.meta)


_default_service: Optional[VoiceEnhanceService] = None


def get_voice_enhance_service() -> VoiceEnhanceService:
    global _default_service
    if _default_service is None:
        _default_service = VoiceEnhanceService()
    return _default_service


def set_voice_enhance_service(service: VoiceEnhanceService) -> None:
    global _default_service
    _default_service = service
