from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Dict, Optional

import pytest
from fastapi import HTTPException

from engines.canvas_commands.models import CommandEnvelope
from engines.canvas_commands.service import (
    apply_command,
    get_canvas_snapshot,
    get_canvas_replay,
)
from engines.common.identity import RequestContext
from engines.identity.jwt_service import AuthContext


@pytest.fixture
def context() -> RequestContext:
    ctx = RequestContext(
        tenant_id="t_canvas",
        env="dev",
        mode="saas",
        project_id="proj",
        request_id="req",
        user_id="sender",
        surface_id="surface-1",
    )
    ctx.actor_id = ctx.user_id
    return ctx


@pytest.fixture
def auth(context: RequestContext) -> AuthContext:
    return AuthContext(
        user_id=context.user_id or "sender",
        email="canvas@example.com",
        tenant_ids=[context.tenant_id],
        default_tenant_id=context.tenant_id,
        role_map={context.tenant_id: "owner"},
    )


@pytest.fixture(autouse=True)
def stub_dependencies(monkeypatch):
    monkeypatch.setattr("engines.canvas_commands.service.register_canvas_resource", lambda *args, **kwargs: None)
    monkeypatch.setattr("engines.canvas_commands.service.verify_canvas_access", lambda *args, **kwargs: None)
    class GateChainStub:
        def run(self, *args, **kwargs):
            return None
    monkeypatch.setattr("engines.canvas_commands.service.get_gate_chain", lambda: GateChainStub())
    monkeypatch.setattr(
        "engines.canvas_commands.service.publish_message",
        lambda *args, **kwargs: SimpleNamespace(id="published-1"),
    )


@pytest.fixture
def fake_tabular(monkeypatch):
    class FakeTabularStoreService:
        _tables: Dict[str, Dict[str, Dict[str, Dict]]] = {}

        def __init__(self, context, resource_kind="canvas_command_store"):
            self.context = context
            self.resource_kind = resource_kind
            FakeTabularStoreService._tables.setdefault(
                resource_kind,
                {},
            )

        def upsert(self, table_name, key, data):
            tables = FakeTabularStoreService._tables[self.resource_kind]
            tables.setdefault(table_name, {})[key] = data

        def get(self, table_name, key):
            tables = FakeTabularStoreService._tables[self.resource_kind]
            return tables.get(table_name, {}).get(key)

        def list_by_prefix(self, table_name, prefix):
            tables = FakeTabularStoreService._tables[self.resource_kind]
            return [
                data
                for k, data in tables.get(table_name, {}).items()
                if k.startswith(prefix)
            ]

    FakeTabularStoreService._tables = {}
    monkeypatch.setattr(
        "engines.canvas_commands.store_service.TabularStoreService",
        FakeTabularStoreService,
    )
    return FakeTabularStoreService


def _build_command(base_rev: int, idempotency_key: str) -> CommandEnvelope:
    return CommandEnvelope(
        id="cmd-1",
        type="update_node",
        canvas_id="canvas-1",
        base_rev=base_rev,
        idempotency_key=idempotency_key,
        args={"value": 42},
    )


def test_restart_safe_and_idempotent(context: RequestContext, auth: AuthContext, fake_tabular):
    cmd = _build_command(base_rev=0, idempotency_key="idem-1")
    result = asyncio.run(apply_command(context.tenant_id, auth.user_id, cmd, context=context))
    assert result.current_rev == 1

    snapshot = asyncio.run(get_canvas_snapshot("canvas-1", context.tenant_id, context=context))
    assert snapshot.head_rev == 1
    assert snapshot.head_event_id is not None

    replay = asyncio.run(get_canvas_replay("canvas-1", context.tenant_id, context=context))
    assert len(replay) == 1

    # Replay the same command (idempotent) - head_rev should stay the same
    replay_result = asyncio.run(apply_command(context.tenant_id, auth.user_id, cmd, context=context))
    assert replay_result.current_rev == 1

    # After restart (new context but same routing), replay should still fetch event
    new_context = RequestContext(
        tenant_id=context.tenant_id,
        env=context.env,
        mode=context.mode,
        project_id=context.project_id,
        request_id="req-2",
        user_id=context.user_id,
        surface_id=context.surface_id,
    )
    new_context.actor_id = context.actor_id
    snapshot_after = asyncio.run(get_canvas_snapshot("canvas-1", context.tenant_id, context=new_context))
    assert snapshot_after.head_rev == 1
    replay_after = asyncio.run(get_canvas_replay("canvas-1", context.tenant_id, context=new_context))
    assert replay_after[0].event_id == snapshot_after.head_event_id


def test_invalid_cursor_returns_410(context: RequestContext, auth: AuthContext, fake_tabular):
    cmd = _build_command(base_rev=0, idempotency_key="idem-2")
    asyncio.run(apply_command(context.tenant_id, auth.user_id, cmd, context=context))
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(get_canvas_replay("canvas-1", context.tenant_id, after_event_id="missing", context=context))
    detail = exc_info.value.detail["error"]
    assert exc_info.value.status_code == 410
    assert detail["code"] == "canvas.cursor_invalid"


def test_missing_route_returns_503(monkeypatch, context: RequestContext, auth: AuthContext):
    class MissingTabular:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("no route")

    monkeypatch.setattr("engines.canvas_commands.store_service.TabularStoreService", MissingTabular)
    cmd = _build_command(base_rev=0, idempotency_key="idem-3")
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(apply_command(context.tenant_id, auth.user_id, cmd, context=context))

    detail = exc_info.value.detail["error"]
    assert exc_info.value.status_code == 503
    assert detail["code"] == "canvas_command_store.missing_route"
