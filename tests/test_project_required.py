from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from engines.common.identity import RequestContext, get_request_context

app = FastAPI()


@app.get("/enforce")
def _require_project(context: RequestContext = Depends(get_request_context)) -> dict[str, str]:
    return {"project_id": context.project_id}


client = TestClient(app)


def test_missing_project_returns_400() -> None:
    response = client.get(
        "/enforce", headers={"X-Tenant-Id": "t_test", "X-Mode": "saas"}
    )
    assert response.status_code == 400


def test_project_header_allows_request() -> None:
    response = client.get(
        "/enforce",
        headers={
            "X-Tenant-Id": "t_test",
            "X-Mode": "saas",
            "X-Project-Id": "p_header",
            "X-Surface-Id": "surf",
            "X-App-Id": "app",
        },
    )
    assert response.status_code == 200
    assert response.json()["project_id"] == "p_header"
