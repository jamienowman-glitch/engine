from __future__ import annotations

import os

from fastapi.testclient import TestClient

from engines.chat.service.server import create_app
from engines.identity.repository import InMemoryIdentityRepository
from engines.identity.state import set_identity_repo
from engines.identity.models import Tenant, User, TenantMembership, TenantKeyConfig
from engines.identity.key_service import KeyConfigService
from engines.identity.routes_keys import set_key_service
from engines.common.keys import TenantKeySelector
from engines.identity.jwt_service import JwtService
from engines.budget.service import set_budget_service, BudgetService
from engines.budget.repository import InMemoryBudgetUsageRepository


def _setup():
    repo = InMemoryIdentityRepository()
    set_identity_repo(repo)
    os.environ["APP_ENV"] = "dev"
    os.environ["AUTH_JWT_SIGNING"] = "secret"
    repo.set_key_config(
        TenantKeyConfig(
            tenant_id="system",
            env="prod",
            slot="auth_jwt_signing",
            provider="system",
            secret_name="AUTH_JWT_SIGNING",
        )
    )
    set_key_service(KeyConfigService(repo=repo))
    tenant = Tenant(id="t_demo", name="Demo")
    user = User(email="budget@example.com")
    repo.create_tenant(tenant)
    repo.create_user(user)
    repo.create_membership(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    selector = TenantKeySelector(repo)
    jwt = JwtService(selector)
    token = jwt.issue_token(
        {
            "sub": user.id,
            "email": user.email,
            "tenant_ids": [tenant.id],
            "default_tenant_id": tenant.id,
            "role_map": {tenant.id: "owner"},
        }
    )
    headers = {
        "X-Tenant-Id": tenant.id,
        "X-Mode": "saas",
        "X-Project-Id": "p_demo",
        "Authorization": f"Bearer {token}",
    }
    set_budget_service(BudgetService(repo=InMemoryBudgetUsageRepository()))
    return tenant, headers


def test_budget_usage_record_and_summary():
    tenant, headers = _setup()
    client = TestClient(create_app())
    payload = {
        "tenant_id": tenant.id,
        "env": "dev",
        "surface": "squared",
        "tool_type": "embedding",
        "tool_id": "vector_explorer",
        "provider": "openai",
        "model_or_plan_id": "gpt-4o",
        "tokens_input": 1000,
        "tokens_output": 500,
        "cost": 0.01,
    }
    resp = client.post("/budget/usage", json=payload, headers=headers)
    assert resp.status_code == 200
    resp_list = client.get("/budget/usage", headers=headers)
    assert resp_list.status_code == 200
    assert resp_list.json()["items"]

    resp_summary = client.get("/budget/usage/summary", headers=headers)
    assert resp_summary.status_code == 200
    assert resp_summary.json()["total_events"] >= 1


def test_budget_tenant_isolation():
    tenant, headers = _setup()
    client = TestClient(create_app())
    payload = {
        "tenant_id": tenant.id,
        "env": "dev",
        "surface": "squared",
        "tool_type": "embedding",
        "tool_id": "vector_explorer",
        "provider": "openai",
        "model_or_plan_id": "gpt-4o",
        "tokens_input": 100,
        "tokens_output": 50,
    }
    client.post("/budget/usage", json=payload, headers=headers)

    # different tenant -> 403 on listing
    other_headers = {
        "X-Tenant-Id": "t_other",
        "X-Mode": "saas",
        "X-Project-Id": "p_demo",
        "Authorization": headers["Authorization"],
    }
    resp = client.get("/budget/usage", headers=other_headers)
    assert resp.status_code in {400, 403}
