from fastapi.testclient import TestClient

from engines.chat.service.server import create_app
from engines.video_timeline.service import InMemoryTimelineRepository, TimelineService, set_timeline_service


def setup_module(_module):
    set_timeline_service(TimelineService(repo=InMemoryTimelineRepository()))


def test_project_sequence_track_clip_flow():
    client = TestClient(create_app())

    proj_resp = client.post(
        "/video/projects",
        json={"tenant_id": "t_test", "env": "dev", "user_id": "u1", "title": "Demo", "description": "desc", "tags": []},
    )
    assert proj_resp.status_code == 200
    project = proj_resp.json()

    seq_resp = client.post(
        f"/video/projects/{project['id']}/sequences",
        json={"tenant_id": "t_test", "env": "dev", "user_id": "u1", "project_id": project["id"], "name": "Main", "timebase_fps": 30},
    )
    assert seq_resp.status_code == 200
    sequence = seq_resp.json()

    track_resp = client.post(
        f"/video/sequences/{sequence['id']}/tracks",
        json={"tenant_id": "t_test", "env": "dev", "user_id": "u1", "sequence_id": sequence["id"], "kind": "video", "order": 0},
    )
    assert track_resp.status_code == 200
    track = track_resp.json()

    clip_resp = client.post(
        f"/video/tracks/{track['id']}/clips",
        json={
            "tenant_id": "t_test",
            "env": "dev",
            "user_id": "u1",
            "track_id": track["id"],
            "asset_id": "asset123",
            "in_ms": 0,
            "out_ms": 1000,
            "start_ms_on_timeline": 0,
        },
    )
    assert clip_resp.status_code == 200
    clip = clip_resp.json()

    # list operations
    assert client.get(f"/video/projects/{project['id']}").status_code == 200
    assert client.get(f"/video/projects/{project['id']}/sequences").status_code == 200
    assert client.get(f"/video/sequences/{sequence['id']}/tracks").status_code == 200
    assert client.get(f"/video/tracks/{track['id']}/clips").status_code == 200
    assert client.get(f"/video/clips/{clip['id']}").status_code == 200
