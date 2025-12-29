import tempfile
from pathlib import Path

from engines.media_v2.models import ArtifactCreateRequest, MediaUploadRequest
from engines.media_v2.service import InMemoryMediaRepository, MediaService, set_media_service
from engines.video_render.service import RenderService, set_render_service
from engines.video_timeline.models import Clip, Filter, FilterStack, Sequence, Track, VideoProject
from engines.video_timeline.service import InMemoryTimelineRepository, TimelineService, set_timeline_service
from engines.video_render.tests.helpers import make_video_render_client


def test_render_plan_with_mask_includes_alphamerge():
    media_service = MediaService(repo=InMemoryMediaRepository())
    timeline_service = TimelineService(repo=InMemoryTimelineRepository())
    set_media_service(media_service)
    set_timeline_service(timeline_service)
    set_render_service(RenderService())

    tmp_vid = Path(tempfile.mkdtemp()) / "sample.mp4"
    tmp_vid.write_bytes(b"video")
    asset = media_service.register_remote(
        MediaUploadRequest(tenant_id="t_test", env="dev", user_id="u1", kind="video", source_uri=str(tmp_vid))
    )
    # Register mask artifact
    mask_path = Path(tempfile.mkdtemp()) / "mask.png"
    mask_path.write_bytes(b"mask")
    mask_art = media_service.register_artifact(
        ArtifactCreateRequest(
            tenant_id="t_test",
            env="dev",
            parent_asset_id=asset.id,
            kind="mask",  # type: ignore[arg-type]
            uri=str(mask_path),
        )
    )

    project = timeline_service.create_project(VideoProject(tenant_id="t_test", env="dev", user_id="u1", title="Mask Demo"))
    sequence = timeline_service.create_sequence(Sequence(tenant_id="t_test", env="dev", user_id="u1", project_id=project.id, name="Seq", timebase_fps=30))
    track = timeline_service.create_track(Track(tenant_id="t_test", env="dev", user_id="u1", sequence_id=sequence.id, kind="video", order=0))
    clip = timeline_service.create_clip(
        Clip(
            tenant_id="t_test",
            env="dev",
            user_id="u1",
            track_id=track.id,
            asset_id=asset.id,
            mask_artifact_id=mask_art.id,
            in_ms=0,
            out_ms=1000,
            start_ms_on_timeline=0,
        )
    )
    stack = FilterStack(
        tenant_id="t_test",
        env="dev",
        target_type="clip",
        target_id=clip.id,
        filters=[
            Filter(type="teeth_whiten", params={"intensity": 0.8}, enabled=True)
        ],
    )
    timeline_service.create_filter_stack(stack)

    client = make_video_render_client()
    resp = client.post(
        "/video/render/dry-run",
        json={"tenant_id": "t_test", "env": "dev", "user_id": "u1", "project_id": project.id, "render_profile": "social_1080p_h264", "dry_run": True},
    )
    assert resp.status_code == 200
    plan = resp.json()["plan_preview"]
    # mask adds extra input and alphamerge filter
    assert any("alphamerge" in f for f in plan.get("filters", []))
    assert len(plan.get("inputs", [])) >= 2
    warnings = plan.get("meta", {}).get("warnings", [])
    assert any("video_regions missing" in warning for warning in warnings)
