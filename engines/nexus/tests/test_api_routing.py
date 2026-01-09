import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from engines.nexus.routes import router
from engines.nexus.schemas import NexusIngestRequest, NexusQueryRequest, NexusKind

app = FastAPI()
app.include_router(router)
client = TestClient(app)

def test_ingest_route_accepted():
    payload = {
        "tenantId": "t_acme",
        "env": "dev",
        "kind": "data",
        "docs": [
            {"id": "1", "text": "hello"}
        ]
    }
    response = client.post("/nexus/spaces/main/ingest", json=payload)
    assert response.status_code == 202
    assert "task_id" in response.json()

def test_missing_route_503():
    """Verify 503 canonical error for missing route configuration."""
    payload = {
        "tenantId": "t_missing",
        "env": "dev",
        "kind": "data",
        "docs": []
    }
    response = client.post("/nexus/spaces/main/ingest", json=payload)
    assert response.status_code == 503
    assert response.json()["detail"]["error"]["code"] == "nexus_store.missing_route"

def test_query_route_success():
    payload = {
        "tenantId": "t_acme",
        "env": "dev",
        "kind": "data",
        "query": "hello"
    }
    response = client.post("/nexus/spaces/main/query", json=payload)
    assert response.status_code == 200
    assert "hits" in response.json()

def test_invalid_cursor_410():
    """Verify 410 canonical error for invalid cursor."""
    payload = {
        "tenantId": "t_acme",
        "env": "dev",
        "kind": "data",
        "query": "hello"
    }
    response = client.post("/nexus/spaces/main/query?cursor=invalid", json=payload)
    assert response.status_code == 410
    assert response.json()["detail"]["error"]["code"] == "nexus.cursor_invalid"
