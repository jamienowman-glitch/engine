from __future__ import annotations

import pytest
from fastapi import HTTPException

from engines.common.identity import RequestContext
from engines.firearms.models import FirearmBinding, FirearmGrant
from engines.firearms.repository import RoutedFirearmsRepository
from engines.firearms.routes import (
    FirearmGrantsPayload,
    FirearmPolicyPayload,
    get_policy,
    list_grants,
    put_grants,
    put_policy,
)
from engines.firearms.service import FirearmsService
from engines.identity.jwt_service import AuthContext


@pytest.fixture
def context() -> RequestContext:
    ctx = RequestContext(
        tenant_id="t_test",
        env="dev",
        mode="saas",
        project_id="proj1",
        request_id="req1",
        user_id="user1",
        actor_id="agent1",
    )
    ctx.actor_type = "agent"
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

        def __init__(self, context: RequestContext, resource_kind: str = "firearms_policy_store") -> None:
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

        def delete(self, table_name: str, key: str) -> None:
            FakeTabularStoreService._tables.get(table_name, {}).pop(key, None)

    FakeTabularStoreService._tables = {}
    monkeypatch.setattr("engines.firearms.repository.TabularStoreService", FakeTabularStoreService)
    return FakeTabularStoreService


def _service_with_fake_repo() -> FirearmsService:
    repo = RoutedFirearmsRepository()
    return FirearmsService(repo=repo)


def test_policy_put_get_round_trip(fake_tabular, context: RequestContext, auth: AuthContext):
    service = _service_with_fake_repo()
    payload = FirearmPolicyPayload(
        bindings=[
            FirearmBinding(action_name="tool.dangerous", firearm_id="firearm.db", strategy_lock_required=True),
        ]
    )

    saved = put_policy(payload, context=context, auth=auth, service=service)
    assert len(saved) == 1

    listed = get_policy(context=context, auth=auth, service=service)
    assert len(listed) == 1
    assert listed[0].action_name == "tool.dangerous"
    assert listed[0].firearm_id == "firearm.db"


def test_grants_put_get_round_trip(fake_tabular, context: RequestContext, auth: AuthContext):
    service = _service_with_fake_repo()
    grant = FirearmGrant(
        firearm_id="firearm.db",
        granted_to_agent_id=context.actor_id,
        tenant_id=context.tenant_id,
    )
    saved = put_grants(
        FirearmGrantsPayload(grants=[grant]),
        context=context,
        auth=auth,
        service=service,
    )
    assert len(saved) == 1

    grants = list_grants(agent_id=context.actor_id, context=context, auth=auth, service=service)
    assert len(grants) == 1
    assert grants[0].granted_to_agent_id == context.actor_id
    assert grants[0].firearm_id == "firearm.db"


def test_unlicensed_action_blocks_with_envelope(fake_tabular, context: RequestContext):
    service = _service_with_fake_repo()
    service.bind_action(context, FirearmBinding(action_name="tool.secure", firearm_id="firearm.secure"))

    with pytest.raises(HTTPException) as exc_info:
        service.require_licence_or_raise(context, subject_type="agent", subject_id="agent1", action="tool.secure")

    detail = exc_info.value.detail["error"]
    assert exc_info.value.status_code == 403
    assert detail["code"] == "firearms.license_required"
    assert detail["gate"] == "firearms"
    assert detail["http_status"] == 403


def test_action_allowed_with_grant(fake_tabular, context: RequestContext):
    service = _service_with_fake_repo()
    service.bind_action(context, FirearmBinding(action_name="tool.secure", firearm_id="firearm.secure", strategy_lock_required=False))

    grant = FirearmGrant(
        firearm_id="firearm.secure",
        granted_to_agent_id=context.actor_id,
        tenant_id=context.tenant_id,
    )
    service.grant_licence(context, grant)

    decision = service.check_access(context, "tool.secure")
    assert decision.allowed is True
    assert decision.reason == "grant_valid"


def test_missing_route_returns_503_envelope(monkeypatch, context: RequestContext):
    class MissingRouteTabular:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("no route")

    monkeypatch.setattr("engines.firearms.repository.TabularStoreService", MissingRouteTabular)
    service = _service_with_fake_repo()

    with pytest.raises(HTTPException) as exc_info:
        service.bind_action(context, FirearmBinding(action_name="tool.secure", firearm_id="firearm.secure"))

    detail = exc_info.value.detail["error"]
    assert exc_info.value.status_code == 503
    assert detail["code"] == "firearms_policy_store.missing_route"
    assert detail["http_status"] == 503
