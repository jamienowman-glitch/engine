from engines.video_timeline.models import ParameterAutomation, Keyframe
from engines.video_timeline.service import InMemoryTimelineRepository, TimelineService, set_timeline_service
from engines.video_timeline.tests.helpers import make_timeline_client


def setup_module(_module):
    set_timeline_service(TimelineService(repo=InMemoryTimelineRepository()))


def test_create_list_delete_automation():
    client = make_timeline_client()
    auto_payload = {
        "tenant_id": "t_test",
        "env": "dev",
        "user_id": "u1",
        "target_type": "clip",
        "target_id": "clip123",
        "property": "opacity",
        "keyframes": [{"time_ms": 0, "value": 0.0, "interpolation": "linear"}, {"time_ms": 1000, "value": 1.0, "interpolation": "ease_in"}],
    }
    resp = client.post("/video/automation", json=auto_payload)
    assert resp.status_code == 200
    automation = resp.json()

    resp = client.get("/video/automation", params={"target_type": "clip", "target_id": "clip123"})
    assert resp.status_code == 200
    assert any(a["id"] == automation["id"] for a in resp.json())

    resp = client.delete(f"/video/automation/{automation['id']}")
    assert resp.status_code == 200
