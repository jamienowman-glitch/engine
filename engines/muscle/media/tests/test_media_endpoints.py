from io import BytesIO

from fastapi.testclient import TestClient

from engines.chat.service.server import create_app


class StubBackend:
    def __init__(self):
        self.snippets = []

    def write_snippet(self, kind, doc, tags=None):
        self.snippets.append((doc, tags))
        return {"id": doc.id, "text": doc.text}

    def query_by_tags(self, kind, tags, limit=20):
        # Return stored as NexusDocument-like objects
        return [doc for doc, _tags in self.snippets if tags[0] in (_tags or [])]


class StubGcs:
    def __init__(self):
        self.uploads = []

    def upload_raw_media(self, tenant_id, path, content):
        self.uploads.append((tenant_id, path, content))
        return f"gs://bucket/{tenant_id}/media/{path}"


def test_media_upload_and_list(monkeypatch):
    stub_backend = StubBackend()
    stub_gcs = StubGcs()

    import engines.media.service.routes as routes

    monkeypatch.setattr(routes, "get_backend", lambda: stub_backend)
    monkeypatch.setattr(routes, "GcsClient", lambda: stub_gcs)

    client = TestClient(create_app())
    files = {"file": ("test.txt", BytesIO(b"hello"), "text/plain")}
    resp = client.post("/media/upload", files=files, data={"tenant_id": "t_test"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["asset_id"]
    assert body["gcs_uri"].startswith("gs://bucket/t_test/media/")

    resp = client.get("/media/stack", params={"tenant_id": "t_test"})
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["asset_id"] == stub_backend.snippets[0][0].id
