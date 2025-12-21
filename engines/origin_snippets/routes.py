from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from engines.common.identity import RequestContext, assert_context_matches, get_request_context
from engines.identity.auth import get_auth_context, require_tenant_membership
from engines.media_v2.service import get_media_service
from engines.origin_snippets.models import OriginSnippet, OriginSnippetBatchRequest, OriginSnippetBatchResult
from engines.origin_snippets.service import get_origin_snippets_service

router = APIRouter(prefix="/origin-snippets", tags=["origin_snippets"])


@router.post("/batch", response_model=OriginSnippetBatchResult)
def build_origin_snippets(
    req: OriginSnippetBatchRequest,
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_membership(auth, context.tenant_id)
    assert_context_matches(context, req.tenant_id, req.env)
    try:
        return get_origin_snippets_service().build(req)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/for-audio/{audio_artifact_id}", response_model=OriginSnippetBatchResult)
def get_origin_snippets_for_audio(
    audio_artifact_id: str,
    context: RequestContext = Depends(get_request_context),
    auth=Depends(get_auth_context),
):
    require_tenant_membership(auth, context.tenant_id)
    media = get_media_service()
    artifact = media.get_artifact(audio_artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="audio artifact not found")
    assert_context_matches(context, getattr(artifact, "tenant_id", None), getattr(artifact, "env", None))
    related = [
        art
        for art in media.list_artifacts_for_asset(artifact.parent_asset_id)
        if audio_artifact_id in (art.meta.get("upstream_artifact_ids") or [])
        and art.kind in {"render_snippet", "render"}
        and art.meta.get("op_type") == "origin_snippets.build_v1"
    ]
    snippets = [
        OriginSnippet(
            audio_artifact_id=audio_artifact_id,
            source_asset_id=art.parent_asset_id,
            source_start_ms=art.start_ms or 0.0,
            source_end_ms=art.end_ms or (art.start_ms or 0.0),
            video_artifact_id=art.id,
            meta=art.meta or {},
        )
        for art in related
    ]
    project_id: Optional[str] = related[0].meta.get("project_id") if related else None
    sequence_id: Optional[str] = related[0].meta.get("sequence_id") if related else None
    return OriginSnippetBatchResult(
        snippets=snippets,
        project_id=project_id,
        sequence_id=sequence_id,
        meta={"matched": len(snippets), "source_asset_id": artifact.parent_asset_id},
    )
