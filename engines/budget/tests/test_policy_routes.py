from fastapi import FastAPI
from fastapi.testclient import TestClient

from engines.budget.repository import InMemoryBudgetPolicyRepository, set_budget_policy_repo
from engines.budget.routes import router as budget_router
from engines.identity.auth import get_auth_context
from engines.identity.jwt_service import AuthContext


def _auth_stub() -> AuthContext:
    return AuthContext(
        user_id="u1",
        email="user@example.com",
        tenant_ids=["t_policy"],
        default_tenant_id="t_policy",
        role_map={"t_policy": "owner"},
    )


def _build_client(repo: InMemoryBudgetPolicyRepository) -> TestClient:
    app = FastAPI()
    app.include_router(budget_router)
    app.dependency_overrides[get_auth_context] = lambda: _auth_stub()
    set_budget_policy_repo(repo)
    return TestClient(app)


def _headers():
    return {
        "X-Tenant-Id": "t_policy",
        "X-Project-Id": "p_dev",
        "X-Mode": "lab",
        "X-Surface-Id": "chat",
        "X-App-Id": "chat_app",
    }


def test_put_and_get_policy():
    repo = InMemoryBudgetPolicyRepository()
    client = _build_client(repo)
    headers = _headers()

    put_resp = client.put("/budget/policy", headers=headers, json={"surface": "chat", "threshold": 9.5})
    assert put_resp.status_code == 200
    saved_threshold = float(put_resp.json()["threshold"])
    assert saved_threshold == 9.5

    get_resp = client.get("/budget/policy", headers=headers)
    assert get_resp.status_code == 200
    assert float(get_resp.json()["threshold"]) == saved_threshold


def test_get_policy_not_found():
    repo = InMemoryBudgetPolicyRepository()
    client = _build_client(repo)
    headers = _headers()

    resp = client.get("/budget/policy", headers=headers)
    assert resp.status_code == 404
