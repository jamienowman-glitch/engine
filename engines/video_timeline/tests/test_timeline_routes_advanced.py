
import pytest
from engines.video_timeline.service import set_timeline_service, TimelineService, InMemoryTimelineRepository
from engines.video_timeline.models import VideoProject, Sequence, Track, Clip
from engines.video_timeline.tests.helpers import make_timeline_client

@pytest.fixture
def client():
    # Reset service
    svc = TimelineService(repo=InMemoryTimelineRepository())
    set_timeline_service(svc)
    return make_timeline_client()

def test_trim_route(client):
    # Re-set service just in case fixture scope differs or parallel exec
    svc = TimelineService(repo=InMemoryTimelineRepository())
    set_timeline_service(svc)
    
    # Preset
    p = svc.create_project(VideoProject(tenant_id="t_test", env="dev", title="P"))
    s = svc.create_sequence(Sequence(tenant_id="t_test", env="dev", project_id=p.id, name="S"))
    t = svc.create_track(Track(tenant_id="t_test", env="dev", sequence_id=s.id, kind="video"))
    c = svc.create_clip(Clip(tenant_id="t_test", env="dev", track_id=t.id, asset_id="a1", in_ms=0, out_ms=1000, start_ms_on_timeline=0))
    
    # Use /video prefix (assuming create_app mounts it there)
    resp = client.post(f"/video/clips/{c.id}/trim", json={"new_in_ms": 100, "new_out_ms": 900, "ripple": True})
    
    assert resp.status_code == 200
    data = resp.json()
    assert data["in_ms"] == 100
    assert data["out_ms"] == 900
    
    # Invalid
    resp = client.post(f"/video/clips/{c.id}/trim", json={"new_in_ms": 900, "new_out_ms": 100, "ripple": False})
    # Service raises ValueError -> routes.py catches and raises HTTPException(400)
    assert resp.status_code == 400

def test_multicam_promote_route(client):
    svc = TimelineService(repo=InMemoryTimelineRepository())
    set_timeline_service(svc)
    p = svc.create_project(VideoProject(tenant_id="t_test", env="dev", title="P"))
    
    payload = {
        "name": "MC Seq",
        "result": {
            "tenant_id": "t_test", "env": "dev",
            "cuts": [{"asset_id": "a1", "start_ms": 0, "end_ms": 1000}]
        }
    }
    
    resp = client.post(f"/video/projects/{p.id}/multicam/promote", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "MC Seq"

def test_apply_focus_route(client):
    svc = TimelineService(repo=InMemoryTimelineRepository())
    set_timeline_service(svc)
    p = svc.create_project(VideoProject(tenant_id="t_test", env="dev", title="P"))
    s = svc.create_sequence(Sequence(tenant_id="t_test", env="dev", project_id=p.id, name="S"))
    t = svc.create_track(Track(tenant_id="t_test", env="dev", sequence_id=s.id, kind="video"))
    c = svc.create_clip(Clip(tenant_id="t_test", env="dev", track_id=t.id, asset_id="a1", in_ms=0, out_ms=1000, start_ms_on_timeline=0))
    
    payload = {
        "tenant_id": "t_test", "env": "dev",
        "keyframes": [{"time_ms": 0, "scale": 1.5}]
    }
    resp = client.post(f"/video/clips/{c.id}/focus/apply", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["property"] == "scale"
