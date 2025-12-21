from fastapi.testclient import TestClient
import os

from engines.chat.service.server import create_app
from engines.identity.repository import InMemoryIdentityRepository
from engines.identity.state import set_identity_repo
from engines.identity.models import Tenant, User, TenantMembership, TenantKeyConfig
from engines.identity.key_service import KeyConfigService
from engines.identity.routes_keys import set_key_service
from engines.common.keys import TenantKeySelector
from engines.identity.jwt_service import JwtService
from engines.strategy_lock.repository import InMemoryStrategyLockRepository
from engines.strategy_lock.service import StrategyLockService, set_strategy_lock_service
from engines.strategy_lock.models import StrategyLockCreate, StrategyScope
from engines.common.identity import RequestContext
from engines.kill_switch.models import KillSwitchUpdate
from engines.strategy_lock.models import ACTION_KILL_SWITCH_UPDATE


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
    user = User(email="kill@example.com")
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
    sl_repo = InMemoryStrategyLockRepository()
    sl_service = StrategyLockService(sl_repo)
    set_strategy_lock_service(sl_service)
    ctx = RequestContext(tenant_id=tenant.id, env="dev", user_id=user.id)
    payload = StrategyLockCreate(
        surface=None,
        scope=StrategyScope.other,
        title="Allow kill switch",
        description=None,
        constraints={},
        allowed_actions=[ACTION_KILL_SWITCH_UPDATE],
    )
    lock = sl_service.create_lock(ctx, payload)
    sl_service.approve_lock(ctx, lock.id)
    return tenant, headers


def test_kill_switch_routes():
    tenant, headers = _setup()
    client = TestClient(create_app())
    payload = {"disable_providers": ["aws"]}
    resp = client.put("/kill-switches", json=payload, headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "disable_providers" in body
    get_resp = client.get("/kill-switches", headers=headers)
    assert get_resp.status_code == 200
