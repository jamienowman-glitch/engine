from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import List, Tuple

from engines.align.audio_text_bars.engine import run as align_run
from engines.align.audio_text_bars.types import AlignAudioTextBarsInput
from engines.audio.beat_features.engine import run as beat_run
from engines.audio.beat_features.types import BeatFeaturesInput
from engines.audio.preprocess_basic_clean.engine import run as clean_run
from engines.audio.preprocess_basic_clean.types import PreprocessBasicCleanInput
from engines.audio.segment_ffmpeg.engine import run as segment_run
from engines.audio.segment_ffmpeg.types import SegmentFFmpegInput
from engines.audio_service.models import (
    AlignRequest,
    ArtifactRef,
    AsrRequest,
    BeatFeaturesRequest,
    PreprocessRequest,
    SegmentRequest,
    VoiceEnhanceRequest,
)
from engines.audio_core import asr_backend
from engines.media_v2.models import ArtifactCreateRequest, MediaUploadRequest
from engines.media_v2.service import get_media_service
from engines.storage.gcs_client import GcsClient
from engines.audio_voice_enhance.service import get_voice_enhance_service


class AudioService:
    def __init__(self) -> None:
        self.media_service = get_media_service()
        try:
            self.gcs = GcsClient()
        except Exception:
            self.gcs = None

    def _download_if_gcs(self, uri: str) -> str:
        if uri.startswith("gs://") and self.gcs:
            tmp_path = Path(tempfile.mkdtemp()) / Path(uri).name
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

    def _resolve_paths(self, asset_id: str, artifact_ids: List[str] | None) -> List[Path]:
        paths: List[Path] = []
        if artifact_ids:
            for art_id in artifact_ids:
                art = self.media_service.get_artifact(art_id)
                if art:
                    paths.append(Path(self._download_if_gcs(art.uri)))
        else:
            asset = self.media_service.get_asset(asset_id)
            if asset:
                paths.append(Path(self._download_if_gcs(asset.source_uri)))
        return paths

    def _register_output(self, req, kind: str, path: Path, start_ms: float | None = None, end_ms: float | None = None, meta=None, asset_id_override: str | None = None) -> ArtifactRef:
        uri = str(path)
        if self.gcs:
            try:
                target_asset = asset_id_override or getattr(req, "asset_id", None)
                path_key = f"{target_asset}/{path.name}" if target_asset else f"{path.name}"
                uri = self.gcs.upload_raw_media(req.tenant_id, path_key, path)
            except Exception:
                uri = str(path)
        target_asset_id = asset_id_override or getattr(req, "asset_id", None)
        art = self.media_service.register_artifact(
            ArtifactCreateRequest(
                tenant_id=req.tenant_id,
                env=req.env,
                parent_asset_id=target_asset_id or getattr(req, "asset_id", ""),
                kind=kind,  # type: ignore[arg-type]
                uri=uri,
                start_ms=start_ms,
                end_ms=end_ms,
                meta=meta or {},
            )
        )
        return ArtifactRef(artifact_id=art.id, uri=art.uri, meta=meta or {})

    def preprocess(self, req: PreprocessRequest) -> List[ArtifactRef]:
        paths = self._resolve_paths(req.asset_id, [req.artifact_id] if req.artifact_id else None)
        output_dir = Path(tempfile.mkdtemp(prefix="audio_clean_"))
        res = clean_run(PreprocessBasicCleanInput(input_paths=paths, output_dir=output_dir))
        artifacts: List[ArtifactRef] = []
        for p in res.cleaned_paths:
            artifacts.append(self._register_output(req, "audio_clean", p, start_ms=0.0))
        return artifacts

    def segment(self, req: SegmentRequest) -> List[ArtifactRef]:
        paths = self._resolve_paths(req.asset_id, [req.artifact_id] if req.artifact_id else None)
        if not paths:
            raise ValueError("no source paths")
        src = paths[0]
        output_dir = Path(tempfile.mkdtemp(prefix="audio_segment_"))
        res = segment_run(
            SegmentFFmpegInput(
                input_path=src,
                output_dir=output_dir,
                segment_seconds=req.segment_seconds,
                overlap_seconds=req.overlap_seconds,
            )
        )
        artifacts: List[ArtifactRef] = []
        for seg in res.segments:
            artifacts.append(
                self._register_output(
                    req,
                    "audio_segment",
                    seg.path,
                    start_ms=seg.start_seconds * 1000.0,
                    end_ms=seg.end_seconds * 1000.0,
                )
            )
        return artifacts

    def beat_features(self, req: BeatFeaturesRequest) -> List[ArtifactRef]:
        artifact_ids = req.artifact_ids or ([req.artifact_id] if getattr(req, "artifact_id", None) else [])
        paths = self._resolve_paths(req.asset_id, artifact_ids)
        if not paths:
            raise ValueError("no source paths")
        res = beat_run(BeatFeaturesInput(audio_paths=paths))
        artifacts: List[ArtifactRef] = []
        for path, meta in res.features.items():
            artifacts.append(self._register_output(req, "beat_features", path, start_ms=0.0, meta=meta.dict()))
        return artifacts

    def asr(self, req: AsrRequest) -> List[ArtifactRef]:
        paths = self._resolve_paths(req.asset_id, req.artifact_ids or ([req.artifact_id] if req.artifact_id else None))
        if not paths:
            raise ValueError("no source paths")
        results = asr_backend.transcribe_audio(paths, model_name=req.model_name, device=req.device, compute_type=req.compute_type)
        artifacts: List[ArtifactRef] = []
        for path, res in zip(paths, results):
            tmp_dir = Path(tempfile.mkdtemp(prefix="asr_"))
            out_path = tmp_dir / f"{path.stem}_asr.json"
            out_path.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
            artifacts.append(self._register_output(req, "asr_transcript", out_path, start_ms=0.0, meta={"status": res.get("status", "ok")}))
        return artifacts

    def align(self, req: AlignRequest) -> ArtifactRef:
        artifacts = [self.media_service.get_artifact(aid) for aid in req.asr_artifact_ids]
        paths = [Path(a.uri) for a in artifacts if a]
        asr_payloads = []
        for path in paths:
            try:
                asr_payloads.append(json.loads(path.read_text(encoding="utf-8")))
            except Exception:
                continue
        if not asr_payloads:
            raise ValueError("no ASR payloads")
        res = align_run(AlignAudioTextBarsInput(asr_payloads=asr_payloads, beat_metadata=req.beat_meta))
        tmp_dir = Path(tempfile.mkdtemp(prefix="bars_"))
        out_path = tmp_dir / f"bars_{artifacts[0].parent_asset_id if artifacts else 'unknown'}.json"
        try:
            payload = res.model_dump_json(indent=2)  # type: ignore[attr-defined]
        except Exception:
            payload = res.json()
        out_path.write_text(payload, encoding="utf-8")
        asset_id = artifacts[0].parent_asset_id if artifacts else None
        art_ref = self._register_output(req, "bars", out_path, meta={"count": len(res.bars)}, asset_id_override=asset_id)
        return art_ref

    def voice_enhance(self, req: VoiceEnhanceRequest) -> ArtifactRef:
        result = get_voice_enhance_service().enhance(req)
        return ArtifactRef(artifact_id=result.artifact_id, uri=result.uri, meta=result.meta)


_default_service: AudioService | None = None


def get_audio_service() -> AudioService:
    global _default_service
    if _default_service is None:
        _default_service = AudioService()
    return _default_service
