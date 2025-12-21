from __future__ import annotations

from fastapi.testclient import TestClient
import os

from engines.chat.service.server import create_app
from engines.nexus.vector_explorer import ingest_routes
from engines.nexus.vector_explorer.ingest_service import VectorIngestService, IngestResult
from engines.nexus.vector_explorer.schemas import VectorExplorerItem
from engines.identity.state import set_identity_repo
from engines.identity.repository import InMemoryIdentityRepository
from engines.identity.models import User, Tenant, TenantMembership
from engines.identity.jwt_service import default_jwt_service
from engines.strategy_lock.models import ACTION_VECTOR_INGEST, StrategyLock, StrategyStatus
from engines.strategy_lock.repository import InMemoryStrategyLockRepository
from engines.strategy_lock.service import StrategyLockService, set_strategy_lock_service


class FakeIngestService(VectorIngestService):
    def __init__(self):
        pass

    def ingest(self, **kwargs):
        return IngestResult(
            item=VectorExplorerItem(
                id="asset123",
                label="test",
                tags=[],
                metrics={},
                similarity_score=None,
                source_ref={},
                vector_ref="asset123",
            ),
            gcs_uri="gs://bucket/t_demo/asset123",
        )


def test_ingest_route(monkeypatch):
    monkeypatch.setattr(ingest_routes, "_service", FakeIngestService())
    os.environ["AUTH_JWT_SIGNING"] = "dev-secret"
    repo = InMemoryIdentityRepository()
    set_identity_repo(repo)
    user = repo.create_user(User(email="demo@example.com", password_hash="pw"))
    tenant = repo.create_tenant(Tenant(id="t_demo", name="Demo"))
    repo.create_membership(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    token = default_jwt_service().issue_token(
        {"sub": user.id, "email": user.email, "tenant_ids": [tenant.id], "default_tenant_id": tenant.id, "role_map": {tenant.id: "owner"}}
    )

    sl_repo = InMemoryStrategyLockRepository()
    sl_service = StrategyLockService(sl_repo)
    set_strategy_lock_service(sl_service)
    lock = StrategyLock(
        tenant_id=tenant.id,
        env="dev",
        surface="demo",
        scope="other",
        title="Allow ingest",
        allowed_actions=[ACTION_VECTOR_INGEST],
        created_by_user_id=user.id,
        status=StrategyStatus.approved,
    )
    sl_repo.create(lock)

    client = TestClient(create_app())
    resp = client.post(
        "/vector-explorer/ingest",
        data={
            "space": "demo",
            "content_type": "text",
            "label": "hello",
            "text_content": "hello world",
        },
        headers={"Authorization": f"Bearer {token}", "X-Tenant-Id": "t_demo", "X-Env": "dev"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["asset_id"] == "asset123"


def test_ingest_route_requires_strategy_lock(monkeypatch):
    monkeypatch.setattr(ingest_routes, "_service", FakeIngestService())
    os.environ["AUTH_JWT_SIGNING"] = "dev-secret"
    repo = InMemoryIdentityRepository()
    set_identity_repo(repo)
    user = repo.create_user(User(email="demo2@example.com", password_hash="pw"))
    tenant = repo.create_tenant(Tenant(id="t_demo2", name="Demo2"))
    repo.create_membership(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    token = default_jwt_service().issue_token(
        {"sub": user.id, "email": user.email, "tenant_ids": [tenant.id], "default_tenant_id": tenant.id, "role_map": {tenant.id: "owner"}}
    )
    set_strategy_lock_service(StrategyLockService(InMemoryStrategyLockRepository()))
    client = TestClient(create_app())
    resp = client.post(
        "/vector-explorer/ingest",
        data={
            "space": "demo",
            "content_type": "text",
            "label": "hello",
            "text_content": "hello world",
        },
        headers={"Authorization": f"Bearer {token}", "X-Tenant-Id": tenant.id, "X-Env": "dev"},
    )
    assert resp.status_code == 409
    assert resp.json()["detail"]["error"] == "strategy_lock_required"
