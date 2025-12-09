from __future__ import annotations

from fastapi.testclient import TestClient

from engines.chat.service.server import create_app
from engines.nexus.vector_explorer import ingest_routes
from engines.nexus.vector_explorer.ingest_service import VectorIngestService, IngestResult
from engines.nexus.vector_explorer.schemas import VectorExplorerItem


class FakeIngestService(VectorIngestService):
    def __init__(self):
        pass

    def ingest(self, **kwargs):
        return IngestResult(
            item=VectorExplorerItem(
                id="asset123",
                label="test",
                tags=[],
                metrics={},
                similarity_score=None,
                source_ref={},
                vector_ref="asset123",
            ),
            gcs_uri="gs://bucket/t_demo/asset123",
        )


def test_ingest_route(monkeypatch):
    monkeypatch.setattr(ingest_routes, "_service", FakeIngestService())
    client = TestClient(create_app())
    resp = client.post(
        "/vector-explorer/ingest",
        data={
            "tenant_id": "t_demo",
            "env": "dev",
            "space": "demo",
            "content_type": "text",
            "label": "hello",
            "text_content": "hello world",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["asset_id"] == "asset123"
