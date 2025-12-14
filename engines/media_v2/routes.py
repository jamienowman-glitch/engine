from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Body, File, Form, HTTPException, UploadFile

from engines.common.identity import RequestContext
from engines.media_v2.models import (
    ArtifactCreateRequest,
    DerivedArtifact,
    MediaAsset,
    MediaAssetResponse,
    MediaKind,
    MediaUploadRequest,
)
from engines.media_v2.service import get_media_service

router = APIRouter(prefix="/media-v2", tags=["media_v2"])


def _parse_tags(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    return [t for t in (raw.split(",") if raw else []) if t]


@router.post("/assets", response_model=MediaAsset)
async def create_media_asset(
    file: UploadFile | None = File(None),
    tenant_id: str | None = Form(None),
    env: str | None = Form(None),
    user_id: str | None = Form(None),
    kind: MediaKind | None = Form(None),
    source_uri: str | None = Form(None),
    source_ref: str | None = Form(None),
    tags: str | None = Form(None),
    meta: str | None = Form(None),
    payload: MediaUploadRequest | None = Body(None),
):
    """Create a media asset from either multipart upload or JSON body."""
    service = get_media_service()
    if file:
        if not tenant_id or not env:
            raise HTTPException(status_code=400, detail="tenant_id and env are required for uploads")
        ctx = MediaUploadRequest(
            tenant_id=tenant_id,
            env=env,
            user_id=user_id,
            kind=kind,
            source_uri=source_uri or file.filename,
            source_ref=source_ref,
            tags=_parse_tags(tags),
            meta={},
        )
        content = await file.read()
        return service.register_upload(ctx, file.filename, content)
    if payload:
        return service.register_remote(payload)
    raise HTTPException(status_code=400, detail="Provide either multipart upload or JSON payload")


@router.get("/assets/{asset_id}", response_model=MediaAssetResponse)
def get_media_asset(asset_id: str):
    service = get_media_service()
    res = service.get_asset_with_artifacts(asset_id)
    if not res:
        raise HTTPException(status_code=404, detail="asset not found")
    return res


@router.get("/assets", response_model=List[MediaAsset])
def list_media_assets(tenant_id: str, kind: MediaKind | None = None, tag: str | None = None, source_ref: str | None = None):
    service = get_media_service()
    return service.list_assets(tenant_id=tenant_id, kind=kind, tag=tag, source_ref=source_ref)


@router.post("/assets/{asset_id}/artifacts", response_model=DerivedArtifact)
def create_artifact(
    asset_id: str,
    tenant_id: str = Form(...),
    env: str = Form(...),
    kind: str = Form(...),
    uri: str = Form(...),
    start_ms: float | None = Form(None),
    end_ms: float | None = Form(None),
    track_label: str | None = Form(None),
    meta: str | None = Form(None),
):
    service = get_media_service()
    req = ArtifactCreateRequest(
        tenant_id=tenant_id,
        env=env,
        parent_asset_id=asset_id,
        kind=kind,  # type: ignore[arg-type]
        uri=uri,
        start_ms=start_ms,
        end_ms=end_ms,
        track_label=track_label,
        meta={},
    )
    return service.register_artifact(req)


@router.get("/artifacts/{artifact_id}", response_model=DerivedArtifact)
def get_artifact(artifact_id: str):
    service = get_media_service()
    artifact = service.get_artifact(artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="artifact not found")
    return artifact
