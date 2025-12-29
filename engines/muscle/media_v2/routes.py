from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile

from engines.common.identity import (
    RequestContext,
    assert_context_matches,
    get_request_context,
)
from engines.identity.auth import AuthContext, get_auth_context, require_tenant_membership
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
    user_id: str | None = Form(None),
    kind: MediaKind | None = Form(None),
    source_uri: str | None = Form(None),
    source_ref: str | None = Form(None),
    tags: str | None = Form(None),
    meta: str | None = Form(None),
    payload: MediaUploadRequest | None = Body(None),
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    """Create a media asset from either multipart upload or JSON body."""
    service = get_media_service()
    require_tenant_membership(auth_context, request_context.tenant_id)
    if file:
        ctx = MediaUploadRequest(
            tenant_id=request_context.tenant_id,
            env=request_context.env,
            user_id=auth_context.user_id or request_context.user_id or user_id,
            kind=kind,
            source_uri=source_uri or file.filename,
            source_ref=source_ref,
            tags=_parse_tags(tags),
            meta={},
        )
        content = await file.read()
        return service.register_upload(ctx, file.filename, content)
    if payload:
        assert_context_matches(request_context, payload.tenant_id, payload.env)
        payload_data = payload.model_dump()
        payload_data["tenant_id"] = request_context.tenant_id
        payload_data["env"] = request_context.env
        payload_data["user_id"] = auth_context.user_id or request_context.user_id or payload_data.get("user_id")
        payload_data["tags"] = payload.tags or []
        payload_data["meta"] = payload.meta or {}
        remote_req = MediaUploadRequest(**payload_data)
        return service.register_remote(remote_req)
    raise HTTPException(status_code=400, detail="Provide either multipart upload or JSON payload")


@router.get("/assets/{asset_id}", response_model=MediaAssetResponse)
def get_media_asset(
    asset_id: str,
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    service = get_media_service()
    require_tenant_membership(auth_context, request_context.tenant_id)
    res = service.get_asset_with_artifacts(asset_id)
    if not res:
        raise HTTPException(status_code=404, detail="asset not found")
    # Ideally checking if asset belongs to tenant, but at minimum enforcing auth presence for now
    return res


@router.get("/assets", response_model=List[MediaAsset])
def list_media_assets(
    tenant_id: str,
    kind: MediaKind | None = None,
    tag: str | None = None,
    source_ref: str | None = None,
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    require_tenant_membership(auth_context, tenant_id)
    assert_context_matches(request_context, tenant_id, env=None)
    service = get_media_service()
    return service.list_assets(tenant_id=tenant_id, kind=kind, tag=tag, source_ref=source_ref)


@router.post("/assets/{asset_id}/artifacts", response_model=DerivedArtifact)
def create_artifact(
    asset_id: str,
    kind: str = Form(...),
    uri: str = Form(...),
    start_ms: float | None = Form(None),
    end_ms: float | None = Form(None),
    track_label: str | None = Form(None),
    meta: str | None = Form(None),
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    service = get_media_service()
    require_tenant_membership(auth_context, request_context.tenant_id)
    if auth_context.default_tenant_id != request_context.tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")
    req = ArtifactCreateRequest(
        tenant_id=request_context.tenant_id,
        env=request_context.env,
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
def get_artifact(
    artifact_id: str,
    request_context: RequestContext = Depends(get_request_context),
    auth_context: AuthContext = Depends(get_auth_context),
):
    service = get_media_service()
    require_tenant_membership(auth_context, request_context.tenant_id)
    artifact = service.get_artifact(artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="artifact not found")
    return artifact
