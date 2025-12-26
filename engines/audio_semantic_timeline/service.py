from __future__ import annotations

import json
import logging
import math
import os
import random
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, Tuple

from engines.media_v2.models import ArtifactCreateRequest, DerivedArtifact, MediaAsset
from engines.media_v2.service import get_media_service
from engines.storage.gcs_client import GcsClient
from engines.video_timeline.service import get_timeline_service
from engines.audio_shared.health import build_backend_health_meta, check_dependencies, DependencyInfo
from engines.audio_semantic_timeline.models import (
    AudioEvent,
    AudioEventKind,
    AudioSemanticAnalyzeRequest,
    AudioSemanticAnalyzeResult,
    AudioSemanticTimelineGetResponse,
    AudioSemanticTimelineSummary,
    BeatEvent,
)

logger = logging.getLogger(__name__)

SEMANTIC_BACKEND_ENV = "AUDIO_SEMANTIC_BACKEND"
SEMANTIC_MODEL_ENV = "AUDIO_SEMANTIC_WHISPER_MODEL"
SEMANTIC_SEED_ENV = "AUDIO_SEMANTIC_SEED"
DEFAULT_BACKEND_CHOICE = "whisper_librosa"
SPEED_CHANGE_LIMIT = 1.05


def _probe_duration_ms(path: Path) -> Optional[int]:
    if not path.exists() or shutil.which("ffprobe") is None:
        return None
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    try:
        out = subprocess.check_output(cmd, text=True).strip()
        if out:
            return int(float(out) * 1000)
    except Exception:
        return None
    return None


class AudioSemanticBackend(Protocol):
    def analyze(
        self,
        audio_path: Path,
        include_beats: bool,
        include_speech_music: bool,
        min_silence_ms: int,
        loudness_window_ms: int,
    ) -> AudioSemanticTimelineSummary:
        ...


def _try_import(name: str):
    try:
        return __import__(name)
    except ImportError:
        return None

class WhisperLibrosaBackend:
    """Backend using Whisper + Librosa for real ASR/VAD/beat detection."""

    backend_version = "whisper_librosa_v2"
    backend_type = "whisper_librosa"

    def __init__(self, model_name: Optional[str] = None, seed: int = 42):
        self.model_name = model_name or os.environ.get("AUDIO_SEMANTIC_WHISPER_MODEL", "tiny")
        self._model = None
        self.seed = seed
        self.model_used = f"whisper_{self.model_name}"
        self.random = random.Random(seed)

    def _load_model(self):
        if self._model is None:
            whisper = _try_import("whisper")
            if not whisper:
                raise ImportError("whisper not available")
            self._model = whisper.load_model(self.model_name)
        return self._model

    def _compute_loudness(self, y, sr, start_ms, end_ms):
        if y is None or sr is None:
            return None
        start = int(start_ms * sr / 1000.0)
        end = int(end_ms * sr / 1000.0)
        segment = y[start:end]
        if segment.size == 0:
            return None
        rms = math.sqrt(float((segment ** 2).mean())) if segment.size else 0.0
        return 20 * math.log10(rms + 1e-9)

    def _build_silence_music_events(self, y, sr, speech_windows, include_speech_music, min_silence_ms):
        events: List[AudioEvent] = []
        if y is None or sr is None:
            return events
        import librosa

        non_silent = librosa.effects.split(y, top_db=28)
        cursor = 0
        for start, end in non_silent:
            start_ms = int(start * 1000 / sr)
            end_ms = int(end * 1000 / sr)
            if include_speech_music and any(sw[0] < end_ms and sw[1] > start_ms for sw in speech_windows):
                continue
            loudness = self._compute_loudness(y, sr, start_ms, end_ms)
            if end_ms - start_ms >= min_silence_ms:
                events.append(AudioEvent(kind="music", start_ms=start_ms, end_ms=end_ms, loudness_lufs=loudness, confidence=0.68))
            cursor = end_ms

        # Add silence gaps
        for i in range(len(non_silent) - 1):
            gap_start = int(non_silent[i][1] * 1000 / sr)
            gap_end = int(non_silent[i + 1][0] * 1000 / sr)
            if gap_end - gap_start >= min_silence_ms:
                events.append(AudioEvent(kind="silence", start_ms=gap_start, end_ms=gap_end, loudness_lufs=-60.0, confidence=0.3))
        return events

    def _detect_beats(self, y, sr) -> List[BeatEvent]:
        if y is None or sr is None:
            return []
        import librosa
        tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
        beat_times = librosa.frames_to_time(beat_frames, sr=sr)
        beats: List[BeatEvent] = []
        for idx, t in enumerate(beat_times):
            beats.append(BeatEvent(time_ms=int(t * 1000), beat_index=idx, bar_index=idx // 4, subdivision=None))
        return beats

    def analyze(
        self,
        audio_path: Path,
        include_beats: bool,
        include_speech_music: bool,
        min_silence_ms: int,
        loudness_window_ms: int,
    ) -> AudioSemanticTimelineSummary:
        duration_ms = _probe_duration_ms(audio_path) or 0
        speech_windows: List[Tuple[int, int]] = []
        events: List[AudioEvent] = []
        beats: List[BeatEvent] = []
        y = None
        sr = None

        has_librosa = _try_import("librosa") is not None
        if has_librosa:
            try:
                import librosa
                y, sr = librosa.load(str(audio_path), sr=22050, mono=True)
            except Exception as exc:
                logger.debug("Librosa load failed: %s", exc)
                y = None
                sr = None

        if include_speech_music:
            whisper_mod = _try_import("whisper")
            if whisper_mod:
                try:
                    model = self._load_model()
                    result = model.transcribe(str(audio_path), fp16=False)
                    for seg in result.get("segments", []):
                        start = int(seg["start"] * 1000)
                        end = int(seg["end"] * 1000)
                        text = seg.get("text", "").strip()
                        speech_windows.append((start, end))
                        loudness = self._compute_loudness(y, sr, start, end)
                        events.append(
                            AudioEvent(
                                kind="speech",
                                start_ms=start,
                                end_ms=end,
                                transcription=text,
                                confidence=seg.get("confidence", 0.85),
                                loudness_lufs=loudness,
                            )
                        )
                except Exception as exc:
                    logger.warning("Whisper transcription failed: %s", exc)

        if include_beats and y is not None:
            beats = self._detect_beats(y, sr)

        if include_speech_music and y is not None:
            events.extend(self._build_silence_music_events(y, sr, speech_windows, include_speech_music, min_silence_ms))

        events.sort(key=lambda e: e.start_ms)
        beats.sort(key=lambda b: b.time_ms)

        if not events and not beats:
            stub = StubAudioSemanticBackend()
            return stub.analyze(audio_path, include_beats, include_speech_music, min_silence_ms, loudness_window_ms)

        meta: Dict[str, Any] = {
            "model_used": self.model_used,
            "backend": self.backend_version,
            "semantic_version": self.backend_version,
            "include_beats": include_beats,
            "include_speech_music": include_speech_music,
            "min_silence_ms": min_silence_ms,
            "loudness_window_ms": loudness_window_ms,
            "backend_type": self.backend_type,
            "speed_change_limit": SPEED_CHANGE_LIMIT,
        }
        return AudioSemanticTimelineSummary(
            asset_id="",
            duration_ms=duration_ms,
            events=events,
            beats=beats,
            meta=meta,
        )

class StubAudioSemanticBackend:
    """Lightweight deterministic backend for contract validation."""

    backend_version = "audio_semantic_stub_v1"
    model_used = backend_version
    backend_type = "stub"

    def analyze(
        self,
        audio_path: Path,
        include_beats: bool,
        include_speech_music: bool,
        min_silence_ms: int,
        loudness_window_ms: int,
    ) -> AudioSemanticTimelineSummary:
        duration_ms = _probe_duration_ms(audio_path) or 60000
        events: List[AudioEvent] = []
        cursor = 0
        pattern: List[Tuple[AudioEventKind, int]] = [
            ("speech", 5000),
            ("silence", max(min_silence_ms, 800)),
            ("music", 8000),
            ("speech", 4000),
            ("other", 3000),
        ]
        idx = 0
        while cursor < duration_ms:
            kind, span = pattern[idx % len(pattern)]
            end = min(duration_ms, cursor + span)
            if include_speech_music or kind == "silence" or kind == "other":
                events.append(
                    AudioEvent(
                        kind=kind,
                        start_ms=int(cursor),
                        end_ms=int(end),
                        loudness_lufs=-20.0 + (idx % 4),
                        confidence=0.6,
                    )
                )
            cursor = end
            idx += 1
        beats: List[BeatEvent] = []
        if include_beats:
            beat_interval = 500
            t = 0
            beat_idx = 0
            while t < duration_ms:
                beats.append(BeatEvent(time_ms=int(t), beat_index=beat_idx, bar_index=beat_idx // 4, subdivision=None))
                t += beat_interval
                beat_idx += 1
        return AudioSemanticTimelineSummary(
            asset_id="",
            duration_ms=duration_ms,
            events=events,
            beats=beats,
            meta={
            "model_used": self.model_used,
            "semantic_version": self.backend_version,
            "backend": self.backend_version,
            "backend_type": self.backend_type,
            "include_beats": include_beats,
            "include_speech_music": include_speech_music,
            "min_silence_ms": min_silence_ms,
            "loudness_window_ms": loudness_window_ms,
            "speed_change_limit": SPEED_CHANGE_LIMIT,
            },
        )


class AudioSemanticService:
    def __init__(self, backend: Optional[AudioSemanticBackend] = None) -> None:
        self.backend = backend or self._build_default_backend()
        self.media_service = get_media_service()
        self.timeline_service = get_timeline_service()
        try:
            self.gcs = GcsClient()
        except Exception:
            self.gcs = None

    @staticmethod
    def _build_default_backend() -> AudioSemanticBackend:
        backend_choice = os.environ.get("AUDIO_SEMANTIC_BACKEND", "whisper_librosa")
        has_deps = _try_import("librosa") is not None and _try_import("whisper") is not None
        if backend_choice.startswith("whisper") and has_deps:
            model_name = os.environ.get("AUDIO_SEMANTIC_WHISPER_MODEL", "tiny")
            seed = int(os.environ.get("AUDIO_SEMANTIC_SEED", "42"))
            return WhisperLibrosaBackend(model_name=model_name, seed=seed)
        return StubAudioSemanticBackend()

    def _validate_context(self, req: AudioSemanticAnalyzeRequest) -> None:
        if not req.tenant_id or req.tenant_id == "t_unknown":
            raise ValueError("Invalid tenant_id")
        if not req.env:
            raise ValueError("Invalid env")

    def _backend_dependency_name(self) -> str:
        backend_type = getattr(self.backend, "backend_type", "stub")
        if backend_type == "whisper_librosa":
            return "librosa"
        return "stub_backend"

    def _backend_meta(self) -> Dict[str, Any]:
        deps = check_dependencies()
        primary = self._backend_dependency_name()
        if primary not in deps:
            deps = {**deps, primary: DependencyInfo(True, getattr(self.backend, "backend_version", "unknown"), None)}
        return build_backend_health_meta(
            service_name="audio_semantic_timeline",
            backend_type=getattr(self.backend, "backend_type", "stub"),
            primary_dependency=primary,
            dependencies=deps,
        )


    def _cache_key(self, req: AudioSemanticAnalyzeRequest, asset_id: str) -> str:
        backend_version = getattr(self.backend, "backend_version", getattr(self.backend, "model_used", "audio_semantic_stub"))
        user_part = req.user_id or "anonymous"
        return (
            f"{req.tenant_id}|{req.env}|{asset_id}|{req.artifact_id or 'None'}|"
            f"{req.include_beats}|{req.include_speech_music}|"
            f"{req.min_silence_ms}|{req.loudness_window_ms}|"
            f"{backend_version}|{user_part}"
        )

    def _maybe_cached(self, asset_id: str, cache_key: str) -> Optional[DerivedArtifact]:
        for art in self.media_service.list_artifacts_for_asset(asset_id):
            if art.kind == "audio_semantic_timeline" and art.meta.get("audio_semantic_cache_key") == cache_key:
                return art
        return None

    def _download_if_gcs(self, uri: str) -> str:
        if uri.startswith("gs://") and self.gcs:
            tmp_path = Path(tempfile.mkdtemp(prefix="audio_semantic_src_")) / Path(uri).name
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

    def _resolve_source(self, req: AudioSemanticAnalyzeRequest) -> tuple[MediaAsset, Path]:
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

    def _persist_summary(self, tenant_id: str, asset_id: str, summary: AudioSemanticTimelineSummary) -> str:
        tmp_dir = Path(tempfile.mkdtemp(prefix="audio_semantic_"))
        out_path = tmp_dir / f"{asset_id}_audio_semantic_timeline.json"
        out_path.write_text(json.dumps(summary.model_dump(), indent=2), encoding="utf-8")
        if self.gcs:
            try:
                return self.gcs.upload_raw_media(tenant_id, f"{asset_id}/audio_semantic/{out_path.name}", out_path)
            except Exception:
                return str(out_path)
        return str(out_path)

    def _ensure_audio_path(self, path: Path) -> Path:
        if path.suffix.lower() in {".wav", ".flac", ".mp3", ".aac", ".m4a"}:
            return path
        if shutil.which("ffmpeg") is None:
            return path
        tmp_out = Path(tempfile.mkdtemp(prefix="audio_semantic_audio_")) / f"{path.stem}_audio.wav"
        cmd = ["ffmpeg", "-y", "-i", str(path), "-vn", str(tmp_out)]
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
            return tmp_out
        except Exception:
            return path

    def _register_artifact(self, req: AudioSemanticAnalyzeRequest, asset: MediaAsset, summary: AudioSemanticTimelineSummary, uri: str, backend_meta: Dict[str, Any]) -> DerivedArtifact:
        backend_version = getattr(self.backend, "backend_version", getattr(self.backend, "model_used", "audio_semantic_stub"))
        meta = {
            **summary.meta,
            "backend_info": backend_meta,
        }
        meta.update(
            {
                "include_beats": req.include_beats,
                "include_speech_music": req.include_speech_music,
                "model_used": getattr(self.backend, "model_used", backend_version),
                "backend_version": backend_version,
                "audio_semantic_cache_key": self._cache_key(req, asset.id),
            }
        )
        meta.setdefault("semantic_version", meta.get("backend_version"))
        meta.setdefault("semantic_version", meta.get("backend_version"))
        return self.media_service.register_artifact(
            ArtifactCreateRequest(
                tenant_id=req.tenant_id,
                env=req.env,
                parent_asset_id=asset.id,
                kind="audio_semantic_timeline",  # type: ignore[arg-type]
                uri=uri,
                meta=meta,
            )
        )

    def analyze(self, req: AudioSemanticAnalyzeRequest) -> AudioSemanticAnalyzeResult:
        self._validate_context(req)
        backend_meta = self._backend_meta()
        asset, source_path = self._resolve_source(req)
        audio_path = self._ensure_audio_path(source_path)
        cache_key = self._cache_key(req, asset.id)
        cached = self._maybe_cached(asset.id, cache_key)
        if cached:
            result_meta = {
                **cached.meta,
                "cache_key": cache_key,
                "cache_hit": True,
                "backend_info": backend_meta,
            }
            return AudioSemanticAnalyzeResult(audio_semantic_artifact_id=cached.id, uri=cached.uri, meta=result_meta)
        raw_summary = self.backend.analyze(
            audio_path=audio_path,
            include_beats=req.include_beats,
            include_speech_music=req.include_speech_music,
            min_silence_ms=req.min_silence_ms,
            loudness_window_ms=req.loudness_window_ms,
        )
        summary_meta = {
            **raw_summary.meta,
            "audio_semantic_cache_key": cache_key,
            "backend_info": backend_meta,
            "speed_change_limit": SPEED_CHANGE_LIMIT,
            "backend_type": getattr(self.backend, "backend_type", "stub"),
        }
        summary = raw_summary.model_copy(
            update={
                "asset_id": asset.id,
                "artifact_id": req.artifact_id,
                "meta": summary_meta,
            }
        )
        uri = self._persist_summary(req.tenant_id, asset.id, summary)
        artifact = self._register_artifact(req, asset, summary, uri, backend_meta)
        result_meta = {
            **artifact.meta,
            "cache_key": cache_key,
            "cache_hit": False,
            "backend_info": backend_meta,
        }
        return AudioSemanticAnalyzeResult(
            audio_semantic_artifact_id=artifact.id,
            uri=artifact.uri,
            meta=result_meta,
        )

    def _load_summary(self, artifact: DerivedArtifact) -> AudioSemanticTimelineSummary:
        uri = self._download_if_gcs(artifact.uri)
        payload = Path(uri).read_text(encoding="utf-8")
        summary = AudioSemanticTimelineSummary(**json.loads(payload))
        return summary.model_copy(update={"artifact_id": artifact.id})

    def get_timeline(self, artifact_id: str) -> AudioSemanticTimelineGetResponse:
        artifact = self.media_service.get_artifact(artifact_id)
        if not artifact:
            raise FileNotFoundError("audio semantic artifact not found")
        summary = self._load_summary(artifact)
        return AudioSemanticTimelineGetResponse(
            artifact_id=artifact.id,
            uri=artifact.uri,
            summary=summary,
            artifact_meta=artifact.meta,
        )

    def _find_audio_semantic_artifact(self, asset_id: str) -> Optional[DerivedArtifact]:
        for art in self.media_service.list_artifacts_for_asset(asset_id):
            if art.kind == "audio_semantic_timeline":
                return art
        return None

    def _slice_events(self, events: List[AudioEvent], window: Tuple[float, float]) -> List[AudioEvent]:
        start, end = window
        sliced: List[AudioEvent] = []
        for ev in events:
            if ev.end_ms < start or ev.start_ms > end:
                continue
            adj_start = max(ev.start_ms, start) - start
            adj_end = min(ev.end_ms, end) - start
            sliced.append(ev.model_copy(update={"start_ms": int(adj_start), "end_ms": int(adj_end)}))
        return sliced

    def _slice_beats(self, beats: List[BeatEvent], window: Tuple[float, float]) -> List[BeatEvent]:
        start, end = window
        return [b.model_copy(update={"time_ms": int(b.time_ms - start)}) for b in beats if start <= b.time_ms <= end]

    def get_timeline_for_clip(self, clip_id: str) -> AudioSemanticTimelineGetResponse:
        clip = self.timeline_service.get_clip(clip_id)
        if not clip:
            raise FileNotFoundError("clip not found")
        artifact = self._find_audio_semantic_artifact(clip.asset_id)
        if not artifact:
            raise FileNotFoundError("audio semantic timeline not found for asset")
        summary = self._load_summary(artifact)
        window = (clip.in_ms, clip.out_ms)
        sliced_events = self._slice_events(summary.events, window)
        sliced_beats = self._slice_beats(summary.beats, window)
        sliced_meta = {
            **summary.meta,
            "clip_window_ms": list(window),
            "clip_relative": True,
            "speed_change_limit": SPEED_CHANGE_LIMIT,
            "speed_change": clip.speed,
            "speed_change_limited": clip.speed != 1.0,
        }
        sliced = summary.model_copy(
            update={
                "events": sliced_events,
                "beats": sliced_beats,
                "meta": sliced_meta,
            }
        )
        return AudioSemanticTimelineGetResponse(
            artifact_id=artifact.id,
            uri=artifact.uri,
            summary=sliced,
            artifact_meta=artifact.meta,
        )


_default_service: Optional[AudioSemanticService] = None


def get_audio_semantic_service() -> AudioSemanticService:
    global _default_service
    if _default_service is None:
        _default_service = AudioSemanticService()
    return _default_service


def set_audio_semantic_service(service: AudioSemanticService) -> None:
    global _default_service
    _default_service = service
