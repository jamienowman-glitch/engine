from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
from engines.video_multicam.routes import router
from engines.video_multicam.service import MultiCamService, get_multicam_service
from engines.video_multicam.models import MultiCamSession, MultiCamTrackSpec
from engines.media_v2.models import MediaAsset
from engines.video_timeline.models import VideoProject, Sequence, Track, Clip

app = FastAPI()
app.include_router(router)
client = TestClient(app)

def test_build_sequence_endpoint():
    mock_media = MagicMock()
    mock_media.get_asset.side_effect = lambda aid: MediaAsset(id="a1", tenant_id="t1", env="dev", kind="video", duration_ms=1000, source_uri="gs://") if aid == "a1" else None
    
    mock_timeline = MagicMock()
    mock_timeline.create_project.return_value = VideoProject(id="p1", tenant_id="t1", env="dev", title="P")
    mock_timeline.create_sequence.return_value = Sequence(id="s1", project_id="p1", tenant_id="t1", env="dev", name="S")
    # Return mocked objects with IDs so attributes work
    mock_timeline.create_track.return_value = Track(id="tr1", sequence_id="s1", tenant_id="t1", env="dev", kind="video")
    mock_timeline.create_clip.return_value = Clip(id="c1", track_id="tr1", tenant_id="t1", env="dev", asset_id="a1", start_ms_on_timeline=0, in_ms=0, out_ms=1000)

    service = MultiCamService(media_service=mock_media, timeline_service=mock_timeline)
    session = MultiCamSession(
        tenant_id="t1", env="dev", name="Seq Remote", 
        tracks=[{"asset_id": "a1", "role": "primary"}]
    )
    service.repo.create(session)
    
    app.dependency_overrides[get_multicam_service] = lambda: service

    resp = client.post(f"/video/multicam/sessions/{session.id}/build-sequence", json={
        "tenant_id": "t1",
        "env": "dev",
        "session_id": session.id
    })
    assert resp.status_code == 200
    res = resp.json()
    assert res["sequence_id"] == "s1"
