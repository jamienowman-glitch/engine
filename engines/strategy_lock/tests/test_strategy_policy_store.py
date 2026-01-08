from __future__ import annotations

import pytest
from fastapi import HTTPException

from engines.common.identity import RequestContext
from engines.identity.jwt_service import AuthContext
from engines.strategy_lock.policy import (
    RoutedStrategyPolicyRepository,
    StrategyPolicyBinding,
    StrategyPolicyService,
    set_strategy_policy_service,
)
from engines.strategy_lock.routes import (
    StrategyPolicyPayload,
    get_strategy_policy,
    put_strategy_policy,
)


@pytest.fixture
def context() -> RequestContext:
    ctx = RequestContext(
        tenant_id="t_policy",
        env="dev",
        mode="saas",
        project_id="proj1",
        request_id="req1",
        user_id="user1",
    )
    ctx.actor_id = "agent1"
    return ctx


@pytest.fixture
def auth(context: RequestContext) -> AuthContext:
    return AuthContext(
        user_id=context.user_id or "user1",
        email="u@example.com",
        tenant_ids=[context.tenant_id],
        default_tenant_id=context.tenant_id,
        role_map={context.tenant_id: "owner"},
    )


@pytest.fixture
def fake_tabular(monkeypatch):
    class FakeTabularStoreService:
        _tables: dict[str, dict[str, dict]] = {}

        def __init__(self, context: RequestContext, resource_kind: str = "strategy_policy_store") -> None:
            self.context = context
            self.resource_kind = resource_kind

        def upsert(self, table_name: str, key: str, data: dict) -> None:
            table = FakeTabularStoreService._tables.setdefault(table_name, {})
            table[key] = data

        def get(self, table_name: str, key: str):
            return FakeTabularStoreService._tables.get(table_name, {}).get(key)

        def list_by_prefix(self, table_name: str, key_prefix: str):
            table = FakeTabularStoreService._tables.get(table_name, {})
            return [record for k, record in table.items() if k.startswith(key_prefix)]

    FakeTabularStoreService._tables = {}
    monkeypatch.setattr(
        "engines.strategy_lock.policy.TabularStoreService",
        FakeTabularStoreService,
    )
    return FakeTabularStoreService


@pytest.fixture
def policy_service(fake_tabular):
    service = StrategyPolicyService(repo=RoutedStrategyPolicyRepository())
    set_strategy_policy_service(service)
    return service


def test_policy_put_get_round_trip(context: RequestContext, auth: AuthContext, policy_service: StrategyPolicyService):
    binding = StrategyPolicyBinding(action_name="tool.reagent", requires_strategy_lock=True)
    payload = StrategyPolicyPayload(bindings=[binding])

    saved = put_strategy_policy(
        payload=payload,
        context=context,
        auth=auth,
        service=policy_service,
    )
    assert len(saved) == 1
    assert saved[0].action_name == "tool.reagent"

    listed = get_strategy_policy(
        context=context,
        auth=auth,
        service=policy_service,
    )
    assert len(listed) == 1
    assert listed[0].requires_strategy_lock is True


def test_requires_strategy_lock_surface_preference(context: RequestContext, policy_service: StrategyPolicyService):
    surface_binding = StrategyPolicyBinding(
        action_name="canvas.paint",
        surface_id="board-1",
        requires_strategy_lock=True,
    )
    policy_service.save_policies(context, [surface_binding])

    assert policy_service.requires_strategy_lock(context, "canvas.paint", surface_id="board-1") is True
    assert policy_service.requires_strategy_lock(context, "canvas.paint", surface_id="board-2") is False


def test_missing_route_returns_503(monkeypatch, context: RequestContext):
    class MissingTabular:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("no route configured")

    monkeypatch.setattr("engines.strategy_lock.policy.TabularStoreService", MissingTabular)
    service = StrategyPolicyService()
    set_strategy_policy_service(service)

    with pytest.raises(HTTPException) as exc_info:
        service.list_policies(context)

    detail = exc_info.value.detail["error"]
    assert exc_info.value.status_code == 503
    assert detail["code"] == "strategy_policy_store.missing_route"
