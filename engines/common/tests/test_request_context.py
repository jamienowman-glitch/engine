from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from engines.common.identity import RequestContext, get_request_context

app = FastAPI()


@app.api_route("/context", methods=["GET", "POST"])
def _context_sample(context: RequestContext = Depends(get_request_context)) -> dict[str, str]:
    return {
        "tenant_id": context.tenant_id,
        "env": context.env,
        "project_id": context.project_id,
    }


client = TestClient(app)
BASE_HEADERS = {
    "X-Tenant-Id": "t_test",
    "X-Env": "dev",
    "X-Project-Id": "p_required",
}


def test_missing_project_id_errors_400() -> None:
    headers = {k: v for k, v in BASE_HEADERS.items() if k != "X-Project-Id"}
    response = client.get("/context", headers=headers)
    assert response.status_code == 400
    assert response.json()["detail"] == "project_id is required"


def test_project_header_allowed() -> None:
    response = client.get("/context", headers=BASE_HEADERS)
    assert response.status_code == 200
    assert response.json()["project_id"] == "p_required"


def test_project_query_fallback() -> None:
    headers = {"X-Tenant-Id": "t_test", "X-Env": "dev"}
    response = client.get("/context", headers=headers, params={"project_id": "project-query"})
    assert response.status_code == 200
    assert response.json()["project_id"] == "project-query"


def test_project_body_fallback() -> None:
    response = client.post(
        "/context",
        json={"tenant_id": "t_body", "env": "dev", "project_id": "project-body"},
    )
    assert response.status_code == 200
    assert response.json()["project_id"] == "project-body"


def test_project_required() -> None:
    """Gate 5: Validate that project_id is mandatory for all requests."""
    # Test 1: Missing project_id must error 400
    headers_no_project = {
        "X-Tenant-Id": "t_test",
        "X-Env": "dev",
    }
    response = client.get("/context", headers=headers_no_project)
    assert response.status_code == 400
    assert "project_id" in response.json()["detail"]

    # Test 2: Valid project_id must succeed
    headers_with_project = {
        "X-Tenant-Id": "t_test",
        "X-Env": "dev",
        "X-Project-Id": "p_valid",
    }
    response = client.get("/context", headers=headers_with_project)
    assert response.status_code == 200
    assert response.json()["project_id"] == "p_valid"
