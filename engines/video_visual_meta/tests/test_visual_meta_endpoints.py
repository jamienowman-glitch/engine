import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from engines.chat.service.server import create_app
from engines.media_v2.models import MediaUploadRequest
from engines.media_v2.service import InMemoryMediaRepository, MediaService, set_media_service
from engines.video_visual_meta.models import VisualMetaSummary
from engines.video_visual_meta.service import StubVisualMetaBackend, VisualMetaService, set_visual_meta_service
from engines.video_timeline.models import VideoProject, Sequence, Track, Clip
from engines.video_timeline.service import InMemoryTimelineRepository, TimelineService, get_timeline_service, set_timeline_service


def setup_module(_module):
    set_media_service(MediaService(repo=InMemoryMediaRepository()))
    set_visual_meta_service(VisualMetaService(backend=StubVisualMetaBackend()))
    set_timeline_service(TimelineService(repo=InMemoryTimelineRepository()))


def test_analyze_and_get_visual_meta_round_trip():
    media_service = MediaService(repo=InMemoryMediaRepository())
    set_media_service(media_service)
    set_visual_meta_service(VisualMetaService(backend=StubVisualMetaBackend()))
    set_timeline_service(TimelineService(repo=InMemoryTimelineRepository()))
    video_path = Path(tempfile.mkdtemp()) / "video.mp4"
    video_path.write_bytes(b"abc")
    asset = media_service.register_remote(
        MediaUploadRequest(tenant_id="t_test", env="dev", user_id="u1", kind="video", source_uri=str(video_path))
    )

    client = TestClient(create_app())
    headers = {"X-Tenant-Id": "t_test", "X-Env": "dev"}
    resp = client.post(
        "/video/visual-meta/analyze",
        json={
            "tenant_id": "t_test",
            "env": "dev",
            "user_id": "u1",
            "asset_id": asset.id,
            "sample_interval_ms": 400,
        },
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["visual_meta_artifact_id"]
    artifact_id = body["visual_meta_artifact_id"]

    artifact = media_service.get_artifact(artifact_id)
    assert artifact is not None
    assert artifact.kind == "visual_meta"

    resp2 = client.get(f"/video/visual-meta/{artifact_id}", headers=headers)
    assert resp2.status_code == 200
    body2 = resp2.json()
    assert body2["artifact_id"] == artifact_id
    summary = VisualMetaSummary(**body2["summary"])
    assert summary.frames
    assert summary.frames[0].timestamp_ms == 0
    assert summary.frames[0].shot_boundary is True
    centers = [frame.primary_subject_center_x for frame in summary.frames if frame.primary_subject_center_x is not None]
    assert len(centers) >= 2
    assert len(set(centers)) > 1  # wobble should vary per frame


def _seed_timeline_with_clip(asset_id: str):
    timeline = get_timeline_service()
    project = timeline.create_project(
        VideoProject(tenant_id="t_test", env="dev", user_id="u1", title="p1", description=None)
    )
    sequence = timeline.create_sequence(
        Sequence(tenant_id="t_test", env="dev", user_id="u1", project_id=project.id, name="s1", duration_ms=4000)
    )
    track = timeline.create_track(Track(tenant_id="t_test", env="dev", user_id="u1", sequence_id=sequence.id, kind="video", order=0))
    clip = timeline.create_clip(
        Clip(
            tenant_id="t_test",
            env="dev",
            user_id="u1",
            track_id=track.id,
            asset_id=asset_id,
            artifact_id=None,
            in_ms=0.0,
            out_ms=2000.0,
            start_ms_on_timeline=0.0,
        )
    )
    return clip


def test_visual_meta_by_clip_slice_and_reframe_suggestion():
    media_service = MediaService(repo=InMemoryMediaRepository())
    set_media_service(media_service)
    set_timeline_service(TimelineService(repo=InMemoryTimelineRepository()))
    visual_meta_service = VisualMetaService(backend=StubVisualMetaBackend())
    set_visual_meta_service(visual_meta_service)
    video_path = Path(tempfile.mkdtemp()) / "video2.mp4"
    video_path.write_bytes(b"xyz")
    asset = media_service.register_remote(
        MediaUploadRequest(tenant_id="t_test", env="dev", user_id="u1", kind="video", source_uri=str(video_path))
    )
    clip = _seed_timeline_with_clip(asset.id)

    client = TestClient(create_app())
    headers = {"X-Tenant-Id": "t_test", "X-Env": "dev"}
    resp = client.post(
        "/video/visual-meta/analyze",
        json={"tenant_id": "t_test", "env": "dev", "user_id": "u1", "asset_id": asset.id, "sample_interval_ms": 300},
        headers=headers,
    )
    assert resp.status_code == 200
    artifact_id = resp.json()["visual_meta_artifact_id"]

    resp_slice = client.get(f"/video/visual-meta/by-clip/{clip.id}", headers=headers)
    assert resp_slice.status_code == 200
    sliced_summary = VisualMetaSummary(**resp_slice.json()["summary"])
    assert all(0 <= f.timestamp_ms <= 2000 for f in sliced_summary.frames)
    assert resp_slice.json()["artifact_id"] == artifact_id

    resp_reframe = client.post(
        "/video/visual-meta/reframe-suggestion",
        json={
            "tenant_id": "t_test",
            "env": "dev",
            "user_id": "u1",
            "clip_id": clip.id,
            "target_aspect_ratio": "9:16",
            "framing_style": "rule_of_thirds",
        },
        headers=headers,
    )
    assert resp_reframe.status_code == 200
    body = resp_reframe.json()
    autos = body["automation"]
    props = {a["property"] for a in autos}
    assert {"position_x", "position_y", "scale"} == props
    times = [kf["time_ms"] for a in autos for kf in a["keyframes"]]
    assert min(times) >= 0
    assert max(times) <= clip.out_ms - clip.in_ms


def test_visual_meta_analyze_reuses_cached_artifact():
    media_service = MediaService(repo=InMemoryMediaRepository())
    set_media_service(media_service)
    set_visual_meta_service(VisualMetaService(backend=StubVisualMetaBackend()))
    video_path = Path(tempfile.mkdtemp()) / "video3.mp4"
    video_path.write_bytes(b"cached")
    asset = media_service.register_remote(
        MediaUploadRequest(tenant_id="t_test", env="dev", user_id="u1", kind="video", source_uri=str(video_path))
    )

    client = TestClient(create_app())
    headers = {"X-Tenant-Id": "t_test", "X-Env": "dev"}
    payload = {"tenant_id": "t_test", "env": "dev", "user_id": "u1", "asset_id": asset.id, "sample_interval_ms": 250}
    first = client.post("/video/visual-meta/analyze", json=payload, headers=headers)
    assert first.status_code == 200
    first_id = first.json()["visual_meta_artifact_id"]

    second = client.post("/video/visual-meta/analyze", json=payload, headers=headers)
    assert second.status_code == 200
    assert second.json()["visual_meta_artifact_id"] == first_id

    artifacts = [a for a in media_service.list_artifacts_for_asset(asset.id) if a.kind == "visual_meta"]
    assert len(artifacts) == 1


def test_analyze_falls_back_to_stub_on_backend_error():
    class BrokenBackend:
        backend_version = "broken"
        model_used = "broken"

        def analyze(self, video_path, sample_interval_ms, include_labels, detect_shot_boundaries):
            raise ValueError("corrupt input")

    media_service = MediaService(repo=InMemoryMediaRepository())
    set_media_service(media_service)
    set_visual_meta_service(VisualMetaService(backend=BrokenBackend()))

    video_path = Path(tempfile.mkdtemp()) / "video_broken.mp4"
    video_path.write_bytes(b"notavideo")
    asset = media_service.register_remote(
        MediaUploadRequest(tenant_id="t_test", env="dev", user_id="u1", kind="video", source_uri=str(video_path))
    )

    client = TestClient(create_app())
    headers = {"X-Tenant-Id": "t_test", "X-Env": "dev"}
    resp = client.post(
        "/video/visual-meta/analyze",
        json={
            "tenant_id": "t_test",
            "env": "dev",
            "user_id": "u1",
            "asset_id": asset.id,
            "sample_interval_ms": 300,
        },
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["visual_meta_artifact_id"]
