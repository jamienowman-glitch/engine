from __future__ import annotations

import uuid
from typing import List, Optional, Tuple, cast

from engines.media_v2.models import ArtifactCreateRequest, DerivedArtifact
from engines.media_v2.service import MediaService, get_media_service
from engines.origin_snippets.models import (
    OriginSnippet,
    OriginSnippetBatchRequest,
    OriginSnippetBatchResult,
    OriginSnippetRequestItem,
)
from engines.video_render.models import RenderProfile, RenderRequest, RenderResult
from engines.video_render.service import RenderService, get_render_service
from engines.video_timeline.models import Clip, Sequence, Track, VideoProject
from engines.video_timeline.service import TimelineService, get_timeline_service

DEFAULT_RENDER_PROFILE: RenderProfile = cast(RenderProfile, "1080p_30_web")


class OriginSnippetsService:
    def __init__(
        self,
        media_service: Optional[MediaService] = None,
        timeline_service: Optional[TimelineService] = None,
        render_service: Optional[RenderService] = None,
    ) -> None:
        self.media_service = media_service or get_media_service()
        self.timeline_service = timeline_service or get_timeline_service()
        self.render_service = render_service or get_render_service()

    def _compute_window(
        self, artifact, asset, item: OriginSnippetRequestItem
    ) -> Tuple[float, float]:
        if artifact.start_ms is None or artifact.end_ms is None:
            raise ValueError("audio artifact missing start/end window")
        source_start = float(artifact.start_ms)
        source_end = float(artifact.end_ms)
        start_ms = max(0.0, source_start - float(item.padding_ms or 0))
        end_ms = source_end + float(item.padding_ms or 0)
        asset_duration = float(asset.duration_ms) if getattr(asset, "duration_ms", None) is not None else None
        if asset_duration is not None:
            end_ms = min(asset_duration, end_ms)
        if item.max_duration_ms is not None:
            end_ms = min(end_ms, start_ms + float(item.max_duration_ms))
        if end_ms < start_ms:
            end_ms = start_ms
        return start_ms, end_ms

    def _build_snippet(self, req: OriginSnippetBatchRequest, item: OriginSnippetRequestItem) -> OriginSnippet:
        artifact = self.media_service.get_artifact(item.audio_artifact_id)
        if not artifact:
            raise ValueError(f"audio artifact not found: {item.audio_artifact_id}")
        asset = self.media_service.get_asset(artifact.parent_asset_id)
        if not asset:
            raise ValueError(f"parent asset not found for artifact: {artifact.parent_asset_id}")
        start_ms, end_ms = self._compute_window(artifact, asset, item)
        meta = {
            "padding_ms": item.padding_ms,
            "artifact_start_ms": artifact.start_ms,
            "artifact_end_ms": artifact.end_ms,
            "asset_duration_ms": getattr(asset, "duration_ms", None),
            "op_type": "origin_snippets.build_v1",
            "op_version": "v1",
        }
        if item.max_duration_ms is not None:
            meta["max_duration_ms"] = item.max_duration_ms
        return OriginSnippet(
            audio_artifact_id=item.audio_artifact_id,
            source_asset_id=artifact.parent_asset_id,
            source_start_ms=start_ms,
            source_end_ms=end_ms,
            meta=meta,
        )

    def _ensure_timeline(
        self, req: OriginSnippetBatchRequest, snippets: List[OriginSnippet]
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        if not snippets:
            return None, None, None

        project: Optional[VideoProject] = None
        if req.attach_to_project_id:
            project = self.timeline_service.get_project(req.attach_to_project_id)
            if not project:
                raise ValueError("attach_to_project_id not found")
            if getattr(project, "tenant_id", None) != req.tenant_id or getattr(project, "env", None) != req.env:
                raise ValueError("attach_to_project_id tenant/env mismatch")
        else:
            project = self.timeline_service.create_project(
                VideoProject(
                    tenant_id=req.tenant_id,
                    env=req.env,
                    user_id=req.user_id,
                    title=f"Origin snippets {uuid.uuid4().hex[:6]}",
                    render_profile=req.render_profile or DEFAULT_RENDER_PROFILE,
                    meta={"origin_snippets": True, "op_type": "origin_snippets.build_v1"},
                )
            )

        sequence_fields = {
            "project_id": project.id,
            "tenant_id": req.tenant_id,
            "env": req.env,
            "user_id": req.user_id,
            "name": f"origin-snippets-{uuid.uuid4().hex[:6]}",
            "meta": {"origin_snippets": True},
        }
        if req.attach_to_project_id and getattr(project, "created_at", None):
            sequence_fields["created_at"] = getattr(project, "created_at")
            sequence_fields["updated_at"] = getattr(project, "updated_at", getattr(project, "created_at"))
        sequence = self.timeline_service.create_sequence(Sequence(**sequence_fields))  # type: ignore[arg-type]
        track = self.timeline_service.create_track(
            Track(
                sequence_id=sequence.id,
                tenant_id=req.tenant_id,
                env=req.env,
                user_id=req.user_id,
                kind="video",
                order=0,
                meta={"label": "origin"},
            )
        )
        for snippet in snippets:
            clip = self.timeline_service.create_clip(
                Clip(
                    track_id=track.id,
                    tenant_id=req.tenant_id,
                    env=req.env,
                    user_id=req.user_id,
                    asset_id=snippet.source_asset_id,
                    in_ms=snippet.source_start_ms,
                    out_ms=snippet.source_end_ms,
                    start_ms_on_timeline=snippet.source_start_ms,
                    meta={
                        "origin_snippet": True,
                        "audio_artifact_id": snippet.audio_artifact_id,
                        "op_type": "origin_snippets.build_v1",
                    },
                )
            )
            snippet.video_clip_id = clip.id
        return project.id, sequence.id, track.id

    def _register_lineage_artifact(
        self,
        req: OriginSnippetBatchRequest,
        snippet: OriginSnippet,
        render_result: RenderResult,
        project_id: Optional[str],
        sequence_id: Optional[str],
    ) -> DerivedArtifact:
        artifact_meta = {
            "op_type": "origin_snippets.build_v1",
            "op_version": "v1",
            "upstream_artifact_ids": [snippet.audio_artifact_id],
            "source_start_ms": snippet.source_start_ms,
            "source_end_ms": snippet.source_end_ms,
            "render_artifact_id": render_result.artifact_id,
            "render_asset_id": render_result.asset_id,
            "render_profile": render_result.render_profile,
            "project_id": project_id,
            "sequence_id": sequence_id,
            "mode": req.mode,
            "audio_artifact_id": snippet.audio_artifact_id,
        }
        if snippet.video_clip_id:
            artifact_meta["clip_id"] = snippet.video_clip_id
        return self.media_service.register_artifact(
            ArtifactCreateRequest(
                tenant_id=req.tenant_id,
                env=req.env,
                parent_asset_id=snippet.source_asset_id,
                kind="render_snippet",
                uri=render_result.uri,
                start_ms=snippet.source_start_ms,
                end_ms=snippet.source_end_ms,
                meta=artifact_meta,
            )
        )

    def _render_snippets(
        self,
        req: OriginSnippetBatchRequest,
        snippets: List[OriginSnippet],
        project_id: str,
        sequence_id: Optional[str],
    ) -> None:
        profile = cast(RenderProfile, req.render_profile or DEFAULT_RENDER_PROFILE)
        for snippet in snippets:
            render_req = RenderRequest(
                tenant_id=req.tenant_id,
                env=req.env,
                user_id=req.user_id,
                project_id=project_id,
                start_ms=snippet.source_start_ms,
                end_ms=snippet.source_end_ms,
                render_profile=profile,
            )
            render_result = self.render_service.render(
                render_req,
                artifact_kind="render_snippet",
                meta={
                    "origin_snippet": True,
                    "audio_artifact_id": snippet.audio_artifact_id,
                    "source_start_ms": snippet.source_start_ms,
                    "source_end_ms": snippet.source_end_ms,
                },
            )
            lineage_artifact = self._register_lineage_artifact(req, snippet, render_result, project_id, sequence_id)
            snippet.video_artifact_id = lineage_artifact.id
            snippet.meta.update(
                {
                    "render_profile": profile,
                    "render_artifact_id": render_result.artifact_id,
                    "render_asset_id": render_result.asset_id,
                    "lineage_artifact_id": lineage_artifact.id,
                }
            )

    def build(self, req: OriginSnippetBatchRequest) -> OriginSnippetBatchResult:
        snippets: List[OriginSnippet] = [self._build_snippet(req, item) for item in req.items]
        project_id: Optional[str] = None
        sequence_id: Optional[str] = None
        track_id: Optional[str] = None

        if snippets:
            project_id, sequence_id, track_id = self._ensure_timeline(req, snippets)

        if req.mode == "render_clips" and project_id:
            self._render_snippets(req, snippets, project_id, sequence_id)

        meta = {"mode": req.mode}
        if track_id:
            meta["track_id"] = track_id
        return OriginSnippetBatchResult(snippets=snippets, project_id=project_id, sequence_id=sequence_id, meta=meta)


_default_service: Optional[OriginSnippetsService] = None


def get_origin_snippets_service() -> OriginSnippetsService:
    global _default_service
    if _default_service is None:
        _default_service = OriginSnippetsService()
    return _default_service


def set_origin_snippets_service(service: OriginSnippetsService) -> None:
    global _default_service
    _default_service = service
