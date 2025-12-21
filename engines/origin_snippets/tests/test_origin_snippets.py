from __future__ import annotations

from engines.media_v2.models import ArtifactCreateRequest, MediaUploadRequest
from engines.media_v2.service import InMemoryMediaRepository, MediaService
from engines.origin_snippets.models import OriginSnippetBatchRequest, OriginSnippetRequestItem
from engines.origin_snippets.service import OriginSnippetsService
from engines.video_render.models import RenderPlan, RenderResult
from engines.video_timeline.service import InMemoryTimelineRepository, TimelineService


class FakeRenderService:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def render(self, req, artifact_kind: str = "render", meta: dict | None = None):
        self.calls.append({"req": req, "meta": meta, "kind": artifact_kind})
        plan = RenderPlan(inputs=[], input_meta=[], steps=[], output_path=f"/tmp/{req.project_id}_{len(self.calls)}.mp4", profile=req.render_profile)
        return RenderResult(
            asset_id=f"render_asset_{len(self.calls)}",
            artifact_id=f"render_artifact_{len(self.calls)}",
            uri=plan.output_path,
            render_profile=req.render_profile,
            plan_preview=plan,
        )


def _make_media_service():
    media_service = MediaService(repo=InMemoryMediaRepository())
    asset = media_service.register_remote(
        MediaUploadRequest(tenant_id="t_test", env="dev", user_id="u1", kind="video", source_uri="gs://source/video.mp4")
    )
    asset.duration_ms = 1200
    media_service.repo.assets[asset.id] = asset  # type: ignore[attr-defined]
    artifact = media_service.register_artifact(
        ArtifactCreateRequest(
            tenant_id="t_test",
            env="dev",
            parent_asset_id=asset.id,
            kind="audio_hit",
            uri="gs://source/audio.wav",
            start_ms=200,
            end_ms=400,
        )
    )
    return media_service, asset, artifact


def test_window_mapping_applies_padding_bounds_and_max_duration():
    media_service, asset, artifact = _make_media_service()
    svc = OriginSnippetsService(
        media_service=media_service,
        timeline_service=TimelineService(repo=InMemoryTimelineRepository()),
        render_service=FakeRenderService(),
    )

    req = OriginSnippetBatchRequest(
        tenant_id="t_test",
        env="dev",
        user_id="u1",
        items=[OriginSnippetRequestItem(audio_artifact_id=artifact.id, padding_ms=250, max_duration_ms=500)],
    )

    res = svc.build(req)
    assert len(res.snippets) == 1
    snippet = res.snippets[0]
    assert snippet.source_start_ms == 0  # padded below zero clamps to 0
    assert snippet.source_end_ms == 500  # capped by max_duration
    assert snippet.meta["asset_duration_ms"] == asset.duration_ms


def test_timeline_only_creates_clips_on_origin_track():
    media_service, _, artifact = _make_media_service()
    timeline_service = TimelineService(repo=InMemoryTimelineRepository())
    svc = OriginSnippetsService(
        media_service=media_service,
        timeline_service=timeline_service,
        render_service=FakeRenderService(),
    )

    req = OriginSnippetBatchRequest(
        tenant_id="t_test",
        env="dev",
        user_id="u1",
        items=[OriginSnippetRequestItem(audio_artifact_id=artifact.id, padding_ms=100)],
        mode="timeline_only",
    )
    res = svc.build(req)

    assert res.project_id
    assert res.sequence_id
    tracks = timeline_service.list_tracks_for_sequence(res.sequence_id)
    assert len(tracks) == 1
    clips = timeline_service.list_clips_for_track(tracks[0].id)
    assert len(clips) == 1
    clip = clips[0]
    assert clip.asset_id == res.snippets[0].source_asset_id
    assert clip.in_ms == res.snippets[0].source_start_ms
    assert clip.out_ms == res.snippets[0].source_end_ms
    assert res.snippets[0].video_clip_id == clip.id


def test_render_mode_registers_lineage_artifacts():
    media_service, asset, artifact = _make_media_service()
    render_service = FakeRenderService()
    svc = OriginSnippetsService(
        media_service=media_service,
        timeline_service=TimelineService(repo=InMemoryTimelineRepository()),
        render_service=render_service,
    )

    req = OriginSnippetBatchRequest(
        tenant_id="t_test",
        env="dev",
        user_id="u1",
        items=[OriginSnippetRequestItem(audio_artifact_id=artifact.id, padding_ms=0)],
        mode="render_clips",
        render_profile="1080p_30_web",
    )
    res = svc.build(req)

    assert len(render_service.calls) == 1
    render_call = render_service.calls[0]
    assert render_call["req"].start_ms == res.snippets[0].source_start_ms
    assert render_call["req"].end_ms == res.snippets[0].source_end_ms
    artifacts = [a for a in media_service.list_artifacts_for_asset(asset.id) if a.kind == "render_snippet"]
    assert artifacts, "render_snippet artifact should be registered"
    lineage = artifacts[0]
    assert res.snippets[0].video_artifact_id == lineage.id
    assert artifact.id in lineage.meta.get("upstream_artifact_ids", [])
    assert lineage.meta.get("op_type") == "origin_snippets.build_v1"
