import tempfile
from pathlib import Path

from engines.media_v2.models import MediaUploadRequest
from engines.media_v2.service import InMemoryMediaRepository, MediaService, set_media_service, LocalMediaStorage
from engines.video_timeline.models import Clip, Sequence, Track, VideoProject
from engines.video_timeline.service import InMemoryTimelineRepository, TimelineService, set_timeline_service
from engines.video_render.service import set_render_service, RenderService
from engines.video_render.tests.helpers import make_video_render_client


def test_render_plan_contains_overlay_and_profile():
    media_service = MediaService(repo=InMemoryMediaRepository(), storage=LocalMediaStorage())
    timeline_service = TimelineService(repo=InMemoryTimelineRepository())
    set_media_service(media_service)
    set_timeline_service(timeline_service)
    set_render_service(RenderService())

    tmp_file = Path(tempfile.mkdtemp()) / "sample.mp4"
    tmp_file.write_bytes(b"123")
    asset = media_service.register_remote(
        MediaUploadRequest(tenant_id="t_test", env="dev", user_id="u1", kind="video", source_uri=str(tmp_file))
    )
    project = timeline_service.create_project(VideoProject(tenant_id="t_test", env="dev", user_id="u1", title="Overlay Demo"))
    sequence = timeline_service.create_sequence(Sequence(tenant_id="t_test", env="dev", user_id="u1", project_id=project.id, name="Seq", timebase_fps=30))
    track1 = timeline_service.create_track(Track(tenant_id="t_test", env="dev", user_id="u1", sequence_id=sequence.id, kind="video", order=0))
    track2 = timeline_service.create_track(Track(tenant_id="t_test", env="dev", user_id="u1", sequence_id=sequence.id, kind="video", order=1))
    timeline_service.create_clip(
        Clip(
            tenant_id="t_test",
            env="dev",
            user_id="u1",
            track_id=track1.id,
            asset_id=asset.id,
            in_ms=0,
            out_ms=1000,
            start_ms_on_timeline=0,
        )
    )
    timeline_service.create_clip(
        Clip(
            tenant_id="t_test",
            env="dev",
            user_id="u1",
            track_id=track2.id,
            asset_id=asset.id,
            in_ms=0,
            out_ms=1000,
            start_ms_on_timeline=0,
        )
    )

    client = make_video_render_client()
    resp = client.post(
        "/video/render/dry-run",
        json={"tenant_id": "t_test", "env": "dev", "user_id": "u1", "project_id": project.id, "render_profile": "social_1080p_h264", "dry_run": True},
    )
    assert resp.status_code == 200
    plan = resp.json()["plan_preview"]
    # Expect overlay filter present for two tracks
    assert any("overlay" in f for f in plan.get("filters", []))
    # Profile should reflect social_1080p_h264
    assert plan["profile"] == "social_1080p_h264"
    assert plan["profile"] == "social_1080p_h264"



def test_plan_determinism():
    media_service = MediaService(repo=InMemoryMediaRepository(), storage=LocalMediaStorage())
    timeline_service = TimelineService(repo=InMemoryTimelineRepository())
    set_media_service(media_service)
    set_timeline_service(timeline_service)
    set_render_service(RenderService())

    # 1. Create Data
    tmp_file = Path(tempfile.mkdtemp()) / "sample.mp4"
    tmp_file.write_bytes(b"content")
    asset = media_service.register_remote(
        MediaUploadRequest(tenant_id="t1", env="dev", user_id="u1", kind="video", source_uri=str(tmp_file))
    )
    # Register two proxies that could both match "video_proxy" checks
    from engines.media_v2.models import DerivedArtifact
    media_service.repo.create_artifact(DerivedArtifact(
        id="p1", tenant_id="t1", env="dev", parent_asset_id=asset.id, kind="video_proxy_360p", uri="file:///tmp/p1.mp4"
    ))
    media_service.repo.create_artifact(DerivedArtifact(
        id="p2", tenant_id="t1", env="dev", parent_asset_id=asset.id, kind="video_proxy_360p", uri="file:///tmp/p2.mp4"
    ))

    project = timeline_service.create_project(VideoProject(tenant_id="t1", env="dev", user_id="u1", title="Det Project"))
    seq = timeline_service.create_sequence(Sequence(tenant_id="t1", env="dev", project_id=project.id, name="S1"))
    track = timeline_service.create_track(Track(tenant_id="t1", env="dev", sequence_id=seq.id, kind="video"))
    
    # Clips out of order on insertion, timeline service should handle it, but we want to ensure plan sorts them
    c1 = timeline_service.create_clip(Clip(tenant_id="t1", env="dev", track_id=track.id, asset_id=asset.id, in_ms=0, out_ms=1000, start_ms_on_timeline=1000))
    c2 = timeline_service.create_clip(Clip(tenant_id="t1", env="dev", track_id=track.id, asset_id=asset.id, in_ms=0, out_ms=1000, start_ms_on_timeline=0)) # Earlier

    client = make_video_render_client()
    payload = {
        "tenant_id": "t1", 
        "env": "dev", 
        "user_id": "u1", 
        "project_id": project.id, 
        "render_profile": "preview_720p_fast", # Matches proxy check logic
        "use_proxies": True,
        "dry_run": True
    }

    # 2. Run Twice
    resp1 = client.post("/video/render/dry-run", json=payload)
    assert resp1.status_code == 200
    plan1 = resp1.json()["plan_preview"]

    resp2 = client.post("/video/render/dry-run", json=payload)
    assert resp2.status_code == 200
    plan2 = resp2.json()["plan_preview"]

    # 3. Assert Equality
    # Remove ephemeral fields if any (UUIDs generated during plan usually should be stable if seeded or deterministically derived)
    # Assuming UUIDs for steps/segments might be random?
    # RenderPlan doesn't have random IDs usually, except maybe step IDs if they had them (they don't).
    
    import json
    p1_s = json.dumps(plan1, sort_keys=True)
    p2_s = json.dumps(plan2, sort_keys=True)
    assert p1_s == p2_s
    
    # 4. Verify Meta
    meta = plan1["meta"]
    assert "render_profile" in meta
    assert meta["render_profile"] == "preview_720p_fast"
    assert "encoder_used" in meta
