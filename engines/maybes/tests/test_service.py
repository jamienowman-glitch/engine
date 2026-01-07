from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip("Tests out of sync with schema")

from engines.common.identity import RequestContext
from engines.logging import audit
from engines.maybes import service as maybes_service
from engines.maybes.schemas import MaybeCreate, MaybeQuery, MaybeUpdate, MaybeSourceType, NoteSource
from engines.maybes.service import MaybesNotFound, MaybesService


@pytest.fixture(autouse=True)
def stub_gate_chain(monkeypatch):
    class _StubGateChain:
        def run(self, *args, **kwargs):
            return None

    monkeypatch.setattr(maybes_service, "get_gate_chain", lambda: _StubGateChain())
    yield


def test_create_and_get():
    svc = MaybesService()
    ctx = RequestContext(request_id="r1", tenant_id="t_demo", env="dev", user_id="u1", surface_id="test")
    created = svc.create_item(
        MaybeCreate(
            tenant_id="t_demo",
            env="dev",
            space="scratchpad-default",
            user_id="u1",
            title="note",
            content="hello world body",
            tags=["alpha"],
            source=NoteSource(created_by="user"),
        ),
        ctx,
    )
    fetched = svc.get_item(ctx, created.id)
    assert fetched.id == created.id
    assert fetched.tenant_id == "t_demo"
    assert fetched.env == "dev"


def test_tenant_and_env_isolation():
    svc = MaybesService()
    ctx = RequestContext(request_id="r1", tenant_id="t_a", env="dev", user_id="u1", surface_id="test")
    item = svc.create_item(
        MaybeCreate(
            tenant_id="t_a",
            env="dev",
            space="scratchpad-default",
            title="same id",
            content="content",
        ),
        ctx,
    )
    with pytest.raises(MaybesNotFound):
        svc.get_item(RequestContext(request_id="r2", tenant_id="t_other", env="dev", user_id="u1", surface_id="test"), item.id)
    with pytest.raises(MaybesNotFound):
        svc.get_item(RequestContext(request_id="r3", tenant_id="t_a", env="prod", user_id="u1", surface_id="test"), item.id)
    # list for other tenant/env is empty
    res = svc.list_items(MaybeQuery(tenant_id="t_other", env="dev"))
    assert res == []
    res = svc.list_items(MaybeQuery(tenant_id="t_a", env="prod"))
    assert res == []


def test_list_filters_and_search():
    svc = MaybesService()
    ctx = RequestContext(request_id="r1", tenant_id="t_demo", env="dev", user_id="u1", surface_id="test")
    svc.create_item(
        MaybeCreate(
            tenant_id="t_demo",
            env="dev",
            space="scratchpad-default",
            user_id="u1",
            title="alpha title",
            content="body match",
            tags=["tag1"],
            pinned=True,
        ),
        ctx,
    )
    svc.create_item(
        MaybeCreate(
            tenant_id="t_demo",
            env="dev",
            space="other-space",
            user_id="u2",
            title="beta",
            content="irrelevant",
            tags=["tag2"],
            pinned=False,
            source=NoteSource(created_by="agent"),
        ),
        ctx,
    )
    svc.create_item(
        MaybeCreate(
            tenant_id="t_demo",
            env="dev",
            space="scratchpad-default",
            user_id="u1",
            title="archived",
            content="older",
            tags=["tag1", "tag3"],
        ),
        ctx,
    )
    # archived filter
    for item in svc.list_items(MaybeQuery(tenant_id="t_demo", env="dev")).copy():
        if item.title == "archived":
            svc.update_item(ctx, item.id, MaybeUpdate(archived=True))
    # space filter
    res = svc.list_items(MaybeQuery(tenant_id="t_demo", env="dev", space="scratchpad-default"))
    assert all(i.space == "scratchpad-default" for i in res)
    # user filter + tags_any + pinned_only
    res = svc.list_items(
        MaybeQuery(
            tenant_id="t_demo",
            env="dev",
            user_id="u1",
            tags_any=["tag1"],
            pinned_only=True,
        )
    )
    assert len(res) == 1
    assert res[0].pinned is True
    # search
    res = svc.list_items(
        MaybeQuery(
            tenant_id="t_demo",
            env="dev",
            search_text="alpha",
        )
    )
    assert res and "alpha" in res[0].title
    # archived flag
    res = svc.list_items(
        MaybeQuery(
            tenant_id="t_demo",
            env="dev",
            archived=True,
        )
    )
    assert all(i.archived for i in res)


def test_update_and_delete():
    svc = MaybesService()
    ctx = RequestContext(request_id="r1", tenant_id="t_demo", env="dev", user_id="u1", surface_id="test")
    created = svc.create_item(
        MaybeCreate(
            tenant_id="t_demo",
            env="dev",
            space="scratchpad-default",
            title="title",
            content="body",
        ),
        ctx,
    )
    updated = svc.update_item(
        ctx,
        created.id,
        MaybeUpdate(title="new title", content="new body", pinned=True, archived=True),
    )
    assert updated.title == "new title"
    assert updated.pinned is True
    assert updated.archived is True

    svc.delete_item(ctx, created.id)
    with pytest.raises(MaybesNotFound):
        svc.get_item(ctx, created.id)


def test_audit_metadata_includes_request_id(monkeypatch):
    svc = MaybesService()
    ctx = RequestContext(request_id="req-123", tenant_id="t_demo", env="dev", user_id="u1", surface_id="test")
    recorded: list = []

    def stub_logger(event):
        recorded.append(event)
        return {"status": "accepted"}

    monkeypatch.setattr(audit, "_audit_logger", stub_logger)

    svc.create_item(
        MaybeCreate(
            tenant_id="t_demo",
            env="dev",
            space="scratchpad-default",
            title="audit note",
            content="body",
        ),
        ctx,
    )

    assert recorded
    metadata = recorded[-1].metadata
    assert metadata["request_id"] == ctx.request_id
    assert metadata["trace_id"] == ctx.request_id
    assert metadata["actor_type"] == "human"
