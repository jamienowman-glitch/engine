import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from engines.chat.service.server import create_app
from engines.media_v2.models import ArtifactCreateRequest, MediaUploadRequest
from engines.media_v2.service import InMemoryMediaRepository, MediaService, set_media_service
from engines.video_render.service import RenderService, set_render_service
from engines.video_timeline.models import Clip, Sequence, Track, VideoProject, FilterStack, Filter
from engines.video_timeline.service import InMemoryTimelineRepository, TimelineService, set_timeline_service


def test_render_plan_masked_filter_graph():
    # Setup services
    media_service = MediaService(repo=InMemoryMediaRepository())
    timeline_service = TimelineService(repo=InMemoryTimelineRepository())
    set_media_service(media_service)
    set_timeline_service(timeline_service)
    set_render_service(RenderService())

    # Create dummy assets
    tmp_vid = Path(tempfile.mkdtemp()) / "sample.mp4"
    tmp_vid.write_bytes(b"video")
    asset = media_service.register_remote(
        MediaUploadRequest(tenant_id="t_test", env="dev", user_id="u1", kind="video", source_uri=str(tmp_vid))
    )
    
    # Create mask artifact
    mask_path = Path(tempfile.mkdtemp()) / "mask.png"
    mask_path.write_bytes(b"mask")
    mask_art = media_service.register_artifact(
        ArtifactCreateRequest(
            tenant_id="t_test",
            env="dev",
            parent_asset_id=asset.id,
            kind="mask", # type: ignore
            uri=str(mask_path),
        )
    )

    # Create Project Structure
    project = timeline_service.create_project(VideoProject(tenant_id="t_test", env="dev", user_id="u1", title="Masked Filter Demo"))
    sequence = timeline_service.create_sequence(Sequence(tenant_id="t_test", env="dev", user_id="u1", project_id=project.id, name="Seq", timebase_fps=30))
    track = timeline_service.create_track(Track(tenant_id="t_test", env="dev", user_id="u1", sequence_id=sequence.id, kind="video", order=0))
    clip = timeline_service.create_clip(
        Clip(
            tenant_id="t_test",
            env="dev",
            user_id="u1",
            track_id=track.id,
            asset_id=asset.id,
            in_ms=0,
            out_ms=1000,
            start_ms_on_timeline=0,
        )
    )
    
    # Add a Masked Filter to the Clip
    # e.g. "Teeth Whitening" -> desaturate
    timeline_service.create_filter_stack(
        FilterStack(
            tenant_id="t_test", 
            env="dev", 
            target_type="clip", 
            target_id=clip.id,
            filters=[
                Filter(
                    type="saturation", 
                    params={"amount": -1.0}, # desaturate 
                    enabled=True,
                    mask_artifact_id=mask_art.id # Apply only to mask
                )
            ]
        )
    )

    client = TestClient(create_app())
    resp = client.post(
        "/video/render/dry-run",
        json={"tenant_id": "t_test", "env": "dev", "user_id": "u1", "project_id": project.id, "render_profile": "social_1080p_h264", "dry_run": True},
    )
    assert resp.status_code == 200
    plan = resp.json()["plan_preview"]
    filters = plan.get("filters", [])
    
    # Verify complex graph logic
    # Look for split, filter, alphamerge, and overlay
    
    plan_str = ";".join(filters)
    
    # 1. Split
    assert "split[" in plan_str
    
    # 2. Filter applied (hue=s=0)
    assert "hue=s=0.0" in plan_str
    
    # 3. Alphamerge
    assert "alphamerge" in plan_str
    
    # 4. Overlay
    assert "overlay=eof_action=pass" in plan_str
    
    print(f"Verified Plan Filters: {filters}")
