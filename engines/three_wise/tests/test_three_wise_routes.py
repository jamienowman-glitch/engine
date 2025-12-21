from __future__ import annotations

import os

from fastapi.testclient import TestClient

from engines.chat.service.server import create_app
from engines.common.identity import RequestContext
from engines.identity.repository import InMemoryIdentityRepository
from engines.identity.state import set_identity_repo
from engines.identity.models import Tenant, User, TenantMembership, TenantKeyConfig
from engines.identity.key_service import KeyConfigService
from engines.identity.routes_keys import set_key_service
from engines.common.keys import TenantKeySelector
from engines.identity.jwt_service import JwtService
from engines.strategy_lock.repository import InMemoryStrategyLockRepository
from engines.strategy_lock.service import StrategyLockService, set_strategy_lock_service
from engines.strategy_lock.models import StrategyLock, StrategyStatus
from engines.three_wise.models import Opinion, ThreeWiseVerdict
from engines.three_wise.service import set_three_wise_service, ThreeWiseService
from engines.three_wise.repository import InMemoryThreeWiseRepository


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
    user = User(email="three@example.com")
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
    headers = {"X-Tenant-Id": tenant.id, "X-Env": "dev", "Authorization": f"Bearer {token}"}
    set_three_wise_service(ThreeWiseService(repo=InMemoryThreeWiseRepository()))
    return tenant, headers


def test_three_wise_submit_and_list():
    tenant, headers = _setup()
    client = TestClient(create_app())
    resp = client.post("/three-wise/questions", json={"question": "Should we proceed?"}, headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    rec_id = body["id"]
    assert len(body["opinions"]) == 3
    assert body["verdict"] == ThreeWiseVerdict.unsure.value
    list_resp = client.get("/three-wise/questions", headers=headers)
    assert list_resp.status_code == 200
    assert list_resp.json()
    get_resp = client.get(f"/three-wise/questions/{rec_id}", headers=headers)
    assert get_resp.status_code == 200


def test_strategy_lock_waits_for_three_wise_approval(monkeypatch):
    monkeypatch.setenv("THREE_WISE_MODE", "stub")
    repo = InMemoryThreeWiseRepository()
    svc = ThreeWiseService(repo=repo)
    set_three_wise_service(svc)
    ctx = RequestContext(tenant_id="t_demo", env="dev", user_id="u1")
    record = svc.submit_question(ctx, "Ship it?")

    sl_repo = InMemoryStrategyLockRepository()
    sl_service = StrategyLockService(repo=sl_repo)
    set_strategy_lock_service(sl_service)
    lock = StrategyLock(
        tenant_id=ctx.tenant_id,
        env=ctx.env,
        surface="squared",
        scope="other",
        title="Require 3-wise",
        allowed_actions=["demo:write"],
        three_wise_id=record.id,
        created_by_user_id=ctx.user_id or "u1",
        status=StrategyStatus.approved,
    )
    sl_repo.create(lock)

    try:
        sl_service.require_strategy_lock_or_raise(ctx, "squared", "demo:write")
        assert False, "expected three_wise_verdict_required"
    except Exception as exc:
        from fastapi import HTTPException

        assert isinstance(exc, HTTPException)
        assert exc.status_code == 409
        assert exc.detail["error"] == "three_wise_verdict_required"

    record.verdict = ThreeWiseVerdict.approve
    record.opinions = [Opinion(model_id="m1", content="good", verdict=ThreeWiseVerdict.approve)]
    repo.update(record)
    sl_service.require_strategy_lock_or_raise(ctx, "squared", "demo:write")


class _LLMStub:
    def generate_opinion(self, ctx: RequestContext, question: str, context_text: str | None):
        return Opinion(model_id="llm-test", content="approved", verdict=ThreeWiseVerdict.approve)


def test_three_wise_real_mode_branch(monkeypatch):
    monkeypatch.setenv("THREE_WISE_MODE", "real")
    monkeypatch.setenv("THREE_WISE_COUNT", "2")
    repo = InMemoryThreeWiseRepository()
    svc = ThreeWiseService(repo=repo, llm_client=_LLMStub())
    set_three_wise_service(svc)
    ctx = RequestContext(tenant_id="t_demo", env="dev", user_id="u2")
    rec = svc.submit_question(ctx, "Run the plan?")
    assert rec.verdict == ThreeWiseVerdict.approve
    assert len(rec.opinions) == 2
