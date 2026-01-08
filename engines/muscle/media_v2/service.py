from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Protocol, Tuple

from engines.media_v2.models import (
    ArtifactCreateRequest,
    DerivedArtifact,
    MediaAsset,
    MediaAssetResponse,
    MediaKind,
    MediaUploadRequest,
)
from engines.config import runtime_config

def _backend_version() -> str:
    return os.getenv("MEDIA_V2_BACKEND_VERSION", "media_v2_unknown")
try:
    from google.cloud import firestore  # type: ignore
except Exception:  # pragma: no cover
    firestore = None


class MediaRepository:
    """Abstract repository for media assets/artifacts."""

    def create_asset(self, asset: MediaAsset) -> MediaAsset:
        raise NotImplementedError

    def list_assets(self, tenant_id: str, kind: Optional[MediaKind] = None, tag: Optional[str] = None, source_ref: Optional[str] = None) -> List[MediaAsset]:
        raise NotImplementedError

    def get_asset(self, asset_id: str) -> Optional[MediaAsset]:
        raise NotImplementedError

    def create_artifact(self, artifact: DerivedArtifact) -> DerivedArtifact:
        raise NotImplementedError

    def list_artifacts_for_asset(self, asset_id: str) -> List[DerivedArtifact]:
        raise NotImplementedError

    def get_artifact(self, artifact_id: str) -> Optional[DerivedArtifact]:
        raise NotImplementedError


class MediaStorage(Protocol):
    """Abstract media blob storage."""

    def upload_bytes(self, tenant_id: str, env: str, asset_id: str, filename: str, content: bytes) -> str:
        raise NotImplementedError


def _artifact_pipeline_hash(req: ArtifactCreateRequest) -> str:
    payload = {
        "parent_asset_id": req.parent_asset_id,
        "tenant_id": req.tenant_id,
        "env": req.env,
        "kind": req.kind,
        "uri": req.uri,
        "start_ms": req.start_ms,
        "end_ms": req.end_ms,
        "track_label": req.track_label,
        "meta": req.meta or {},
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


class S3MediaStorage:
    """S3-backed media storage with strict tenant/env prefixing.
    
    GAP-G1: Block LocalMediaStorage fallback. Enforce S3 configuration.
    Raises at init if RAW_BUCKET not configured (fail-fast).
    """

    def __init__(self, bucket_name: Optional[str] = None, client: Optional[object] = None) -> None:
        self.bucket_name = bucket_name or runtime_config.get_raw_bucket()
        if not self.bucket_name:
            raise RuntimeError(
                "RAW_BUCKET config missing for media storage. "
                "Set RAW_BUCKET env var to S3 bucket name to enable media uploads."
            )
        if client is not None:
            self.client = client
        else:
            try:
                import boto3  # type: ignore
            except Exception as exc:  # pragma: no cover - import error path
                raise RuntimeError("boto3 is required for S3 media storage") from exc
            self.client = boto3.client("s3")

    def _key(self, tenant_id: str, env: str, asset_id: str, filename: str) -> str:
        safe_name = Path(filename).name or "upload.bin"
        return f"tenants/{tenant_id}/{env}/media_v2/{asset_id}/{safe_name}"

    def upload_bytes(self, tenant_id: str, env: str, asset_id: str, filename: str, content: bytes) -> str:
        key = self._key(tenant_id, env, asset_id, filename)
        try:
            self.client.put_object(Bucket=self.bucket_name, Key=key, Body=content)
            return f"s3://{self.bucket_name}/{key}"
        except Exception as exc:  # pragma: no cover - network error path
            raise RuntimeError(f"S3 upload failed: {exc}") from exc


class LocalMediaStorage:
    """Local tmp fallback to keep tests/dev working without S3."""

    def upload_bytes(self, tenant_id: str, env: str, asset_id: str, filename: str, content: bytes) -> str:
        safe_name = Path(filename).name or "upload.bin"
        dest = (
            Path(tempfile.gettempdir())
            / "media_v2"
            / "tenants"
            / tenant_id
            / env
            / asset_id
        )
        dest.mkdir(parents=True, exist_ok=True)
        path = dest / safe_name
        path.write_bytes(content)
        return str(path)


class InMemoryMediaRepository(MediaRepository):
    def __init__(self) -> None:
        self.assets: Dict[str, MediaAsset] = {}
        self.artifacts: Dict[str, DerivedArtifact] = {}

    def create_asset(self, asset: MediaAsset) -> MediaAsset:
        self.assets[asset.id] = asset
        return asset

    def list_assets(self, tenant_id: str, kind: Optional[MediaKind] = None, tag: Optional[str] = None, source_ref: Optional[str] = None) -> List[MediaAsset]:
        results = [a for a in self.assets.values() if a.tenant_id == tenant_id]
        if kind:
            results = [a for a in results if a.kind == kind]
        if tag:
            results = [a for a in results if tag in (a.tags or [])]
        if source_ref:
            results = [a for a in results if a.source_ref == source_ref]
        return sorted(results, key=lambda a: a.created_at, reverse=True)

    def get_asset(self, asset_id: str) -> Optional[MediaAsset]:
        return self.assets.get(asset_id)

    def create_artifact(self, artifact: DerivedArtifact) -> DerivedArtifact:
        self.artifacts[artifact.id] = artifact
        return artifact

    def list_artifacts_for_asset(self, asset_id: str) -> List[DerivedArtifact]:
        results = [a for a in self.artifacts.values() if a.parent_asset_id == asset_id]
        return sorted(results, key=lambda a: a.created_at, reverse=True)

    def get_artifact(self, artifact_id: str) -> Optional[DerivedArtifact]:
        return self.artifacts.get(artifact_id)


class FirestoreMediaRepository(MediaRepository):
    """Firestore-backed media repository (tenant/env scoped collections)."""

    def __init__(self, client: Optional[object] = None) -> None:
        if firestore is None:
            raise RuntimeError("google-cloud-firestore not installed")
        project = runtime_config.get_firestore_project()
        self._client = client or firestore.Client(project=project)  # type: ignore[arg-type]

    def _assets_collection(self, tenant_id: str):
        return self._client.collection(f"media_assets_{tenant_id}")

    def _artifacts_collection(self, tenant_id: str):
        return self._client.collection(f"media_artifacts_{tenant_id}")

    def create_asset(self, asset: MediaAsset) -> MediaAsset:
        payload = asset.model_dump()
        self._assets_collection(asset.tenant_id).document(asset.id).set(payload)
        return asset

    def list_assets(self, tenant_id: str, kind: Optional[MediaKind] = None, tag: Optional[str] = None, source_ref: Optional[str] = None) -> List[MediaAsset]:
        col = self._assets_collection(tenant_id)
        query = col.where("tenant_id", "==", tenant_id)
        if kind:
            query = query.where("kind", "==", kind)
        if source_ref:
            query = query.where("source_ref", "==", source_ref)
        docs = list(query.stream())
        assets = []
        for doc in docs:
            data = doc.to_dict()
            if tag and tag not in (data.get("tags") or []):
                continue
            assets.append(MediaAsset(**data))
        return sorted(assets, key=lambda a: a.created_at, reverse=True)

    def get_asset(self, asset_id: str) -> Optional[MediaAsset]:
        # tenant_id is baked into collection name; scan all? assume caller knows tenant via _default creation.
        # Use prefix wildcard not possible; we require tenant embedded in id? Instead scan known tenant collections? fallback: try default from runtime_config.
        tenant = runtime_config.get_tenant_id()
        if tenant:
            snap = self._assets_collection(tenant).document(asset_id).get()
            if snap.exists:
                return MediaAsset(**snap.to_dict())
        return None

    def create_artifact(self, artifact: DerivedArtifact) -> DerivedArtifact:
        payload = artifact.model_dump()
        self._artifacts_collection(artifact.tenant_id).document(artifact.id).set(payload)
        return artifact

    def list_artifacts_for_asset(self, asset_id: str) -> List[DerivedArtifact]:
        tenant = runtime_config.get_tenant_id()
        if not tenant:
            return []
        col = self._artifacts_collection(tenant)
        docs = list(col.where("parent_asset_id", "==", asset_id).stream())
        artifacts = [DerivedArtifact(**d.to_dict()) for d in docs]
        return sorted(artifacts, key=lambda a: a.created_at, reverse=True)

    def get_artifact(self, artifact_id: str) -> Optional[DerivedArtifact]:
        tenant = runtime_config.get_tenant_id()
        if tenant:
            snap = self._artifacts_collection(tenant).document(artifact_id).get()
            if snap.exists:
                return DerivedArtifact(**snap.to_dict())
        return None


def _probe_media(path: Path) -> Tuple[Optional[float], Optional[float], Optional[int], Optional[int], Optional[str], Optional[int]]:
    """Return duration_ms, fps, channels, sample_rate, codec_info, size_bytes."""
    duration_ms = fps = None
    channels = sample_rate = None
    codec = None
    size_bytes = path.stat().st_size if path.exists() else None
    if shutil.which("ffprobe") is None or not path.exists():
        return duration_ms, fps, channels, sample_rate, codec, size_bytes
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "format=duration:stream=avg_frame_rate,channels,sample_rate,codec_name",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    try:
        output = subprocess.check_output(cmd, text=True).splitlines()
        if output:
            try:
                duration_ms = float(output[0]) * 1000.0 if output[0] else None
            except Exception:
                duration_ms = None
            if len(output) >= 2 and output[1]:
                num, denom = output[1].split("/") if "/" in output[1] else (output[1], "1")
                try:
                    fps = float(num) / float(denom)
                except Exception:
                    fps = None
            if len(output) >= 3 and output[2]:
                try:
                    channels = int(output[2])
                except Exception:
                    channels = None
            if len(output) >= 4 and output[3]:
                try:
                    sample_rate = int(float(output[3]))
                except Exception:
                    sample_rate = None
            if len(output) >= 5 and output[4]:
                codec = output[4]
    except Exception:
        return duration_ms, fps, channels, sample_rate, codec, size_bytes
    return duration_ms, fps, channels, sample_rate, codec, size_bytes


class MediaService:
    def __init__(self, repo: Optional[MediaRepository] = None, storage: Optional[MediaStorage] = None) -> None:
        self.repo = repo or self._default_repo()
        self.storage = storage or self._default_storage()

    def _default_repo(self) -> MediaRepository:
        return FirestoreMediaRepository()

    def _default_storage(self) -> MediaStorage:
        return S3MediaStorage()

    def _store_upload(self, req: MediaUploadRequest, asset_id: str, filename: str, content: bytes) -> str:
        """Store bytes to S3. Raises if not configured."""
        try:
            return self.storage.upload_bytes(req.tenant_id, req.env, asset_id, filename, content)
        except Exception as exc:
            raise RuntimeError("media storage unavailable: " + str(exc)) from exc



    def _build_asset(self, ctx: MediaUploadRequest, uri: str, probe_path: Optional[Path] = None, asset_id: Optional[str] = None) -> MediaAsset:
        duration_ms, fps, channels, sample_rate, codec, size_bytes = (None, None, None, None, None, None)
        if probe_path:
            duration_ms, fps, channels, sample_rate, codec, size_bytes = _probe_media(probe_path)
        asset = MediaAsset(
            id=asset_id or uuid.uuid4().hex,
            tenant_id=ctx.tenant_id,
            env=ctx.env,
            user_id=ctx.user_id,
            kind=ctx.kind or "other",
            source_uri=uri,
            duration_ms=duration_ms,
            fps=fps,
            audio_channels=channels,
            sample_rate=sample_rate,
            codec_info=codec,
            size_bytes=size_bytes,
            tags=ctx.tags,
            source_ref=ctx.source_ref,
            meta=ctx.meta,
        )
        return self.repo.create_asset(asset)

    def register_remote(self, req: MediaUploadRequest) -> MediaAsset:
        return self._build_asset(req, req.source_uri, None)

    def register_upload(self, req: MediaUploadRequest, filename: str, content: bytes) -> MediaAsset:
        asset_id = uuid.uuid4().hex
        uri = self._store_upload(req, asset_id, filename, content)
        tmp_path = None
        try:
            tmp_path = Path(tempfile.gettempdir()) / f"probe_{uuid.uuid4().hex}"
            tmp_path.write_bytes(content)
        except Exception:
            tmp_path = None
        return self._build_asset(req, uri, tmp_path, asset_id)

    def list_assets(self, tenant_id: str, kind: Optional[MediaKind] = None, tag: Optional[str] = None, source_ref: Optional[str] = None) -> List[MediaAsset]:
        return self.repo.list_assets(tenant_id=tenant_id, kind=kind, tag=tag, source_ref=source_ref)

    def get_asset(self, asset_id: str) -> Optional[MediaAsset]:
        return self.repo.get_asset(asset_id)

    def get_asset_with_artifacts(self, asset_id: str) -> Optional[MediaAssetResponse]:
        asset = self.repo.get_asset(asset_id)
        if not asset:
            return None
        return MediaAssetResponse(asset=asset, artifacts=self.repo.list_artifacts_for_asset(asset_id))

    def register_artifact(self, req: ArtifactCreateRequest) -> DerivedArtifact:
        metadata = dict(req.meta or {})
        metadata["pipeline_hash"] = _artifact_pipeline_hash(req)
        metadata.setdefault("backend_version", _backend_version())
        artifact = DerivedArtifact(
            parent_asset_id=req.parent_asset_id,
            tenant_id=req.tenant_id,
            env=req.env,
            kind=req.kind,
            uri=req.uri,
            start_ms=req.start_ms,
            end_ms=req.end_ms,
            track_label=req.track_label,
            meta=metadata,
        )
        return self.repo.create_artifact(artifact)

    def get_artifact(self, artifact_id: str) -> Optional[DerivedArtifact]:
        return self.repo.get_artifact(artifact_id)

    def list_artifacts_for_asset(self, asset_id: str) -> List[DerivedArtifact]:
        return self.repo.list_artifacts_for_asset(asset_id)


# Module-level default service for ease of use across engines.
_default_service: Optional[MediaService] = None


def get_media_service() -> MediaService:
    global _default_service
    if _default_service is None:
        _default_service = MediaService()
    return _default_service


def set_media_service(service: MediaService) -> None:
    """Override the default service (useful for tests)."""
    global _default_service
    _default_service = service
