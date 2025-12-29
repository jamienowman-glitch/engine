from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.testclient import TestClient
from engines.budget.repository import InMemoryBudgetUsageRepository
from engines.budget.service import BudgetService, set_budget_service
from engines.nexus.vector_explorer import routes
from engines.nexus.vector_explorer.repository import InMemoryVectorCorpusRepository
from engines.nexus.vector_explorer.schemas import VectorExplorerItem
from engines.nexus.vector_explorer.service import VectorExplorerService
from engines.nexus.vector_explorer.vector_store import ExplorerVectorStore, ExplorerVectorHit
from engines.nexus.embedding import EmbeddingAdapter, EmbeddingResult
from engines.identity.state import set_identity_repo
from engines.identity.repository import InMemoryIdentityRepository
from engines.identity.models import User, Tenant, TenantMembership
from engines.identity.jwt_service import default_jwt_service


def test_vector_explorer_route(monkeypatch):
    class FakeEmbedder(EmbeddingAdapter):
        def embed_text(self, text: str, model_id=None, context=None) -> EmbeddingResult:
            return EmbeddingResult(vector=[1.0, 0.0], model_id="text")

        def embed_image(self, image_uri: str, model_id=None, context=None) -> EmbeddingResult:  # pragma: no cover - unused
            return EmbeddingResult(vector=[0.0, 1.0], model_id="image")

        def embed_image_bytes(self, image_bytes: bytes, model_id=None, context=None) -> EmbeddingResult:  # pragma: no cover - unused
            return EmbeddingResult(vector=[0.0, 1.0], model_id="image")

    class FakeVectorStore(ExplorerVectorStore):
        def query(self, vector, tenant_id, env, space, top_k=10):
            return [ExplorerVectorHit(id="item1", score=1.0, metadata={})]

        def query_by_datapoint_id(self, anchor_id, tenant_id, env, space, top_k=10):
            return [ExplorerVectorHit(id="item1", score=1.0, metadata={})]

        def upsert(self, item_id, vector, tenant_id, env, space, metadata=None):  # pragma: no cover - unused
            return None

    repo = InMemoryVectorCorpusRepository(
        [
            VectorExplorerItem(
                id="item1",
                label="Item 1",
                tags=["tag1"],
                metrics={"size_hint": 1.0},
                source_ref={"uri": "s1"},
            )
        ]
    )

    fake_service = VectorExplorerService(
        repository=repo,
        vector_store=FakeVectorStore(),
        embedder=FakeEmbedder(),
        event_logger=lambda e: None,
        budget_service=BudgetService(repo=InMemoryBudgetUsageRepository()),
    )
    monkeypatch.setattr(routes, "_service", fake_service)

    os.environ["AUTH_JWT_SIGNING"] = "dev-secret"
    repo_id = InMemoryIdentityRepository()
    set_identity_repo(repo_id)
    user = repo_id.create_user(User(email="demo@example.com", password_hash="pw"))
    tenant = repo_id.create_tenant(Tenant(id="t_demo", name="Demo"))
    repo_id.create_membership(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    token = default_jwt_service().issue_token(
        {"sub": user.id, "email": user.email, "tenant_ids": [tenant.id], "default_tenant_id": tenant.id, "role_map": {tenant.id: "owner"}}
    )
    set_budget_service(BudgetService(repo=InMemoryBudgetUsageRepository()))
    app = FastAPI()
    app.include_router(routes.router)
    client = TestClient(app)
    resp = client.get(
        "/vector-explorer/scene",
        params={"space": "demo", "query_mode": "all"},
        headers={
            "Authorization": f"Bearer {token}",
            "X-Tenant-Id": "t_demo",
            "X-Mode": "saas",
            "X-Project-Id": "p_demo",
            "X-Surface-Id": "surf_demo",
            "X-App-Id": "app_demo",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["nodes"][0]["id"] == "item1"


def test_vector_explorer_membership_required(monkeypatch):
    class FakeVectorStore(ExplorerVectorStore):
        def query(self, vector, tenant_id, env, space, top_k=10):
            return []

        def query_by_datapoint_id(self, anchor_id, tenant_id, env, space, top_k=10):  # pragma: no cover - unused
            return []

        def upsert(self, item_id, vector, tenant_id, env, space, metadata=None):  # pragma: no cover - unused
            return None

    os.environ["AUTH_JWT_SIGNING"] = "dev-secret"
    repo_id = InMemoryIdentityRepository()
    set_identity_repo(repo_id)
    user = repo_id.create_user(User(email="demo2@example.com", password_hash="pw"))
    token = default_jwt_service().issue_token(
        {"sub": user.id, "email": user.email, "tenant_ids": [], "default_tenant_id": "", "role_map": {}}
    )
    fake_service = VectorExplorerService(
        repository=InMemoryVectorCorpusRepository(),
        vector_store=FakeVectorStore(),
        embedder=EmbeddingAdapter(),  # type: ignore[arg-type]
        event_logger=lambda e: None,
        budget_service=BudgetService(repo=InMemoryBudgetUsageRepository()),
    )
    monkeypatch.setattr(routes, "_service", fake_service)

    set_budget_service(BudgetService(repo=InMemoryBudgetUsageRepository()))
    app = FastAPI()
    app.include_router(routes.router)
    client = TestClient(app)
    resp = client.get(
        "/vector-explorer/scene",
        params={"space": "demo", "query_mode": "all"},
        headers={
            "X-Tenant-Id": "t_demo",
            "X-Mode": "saas",
            "X-Project-Id": "p_demo",
            "X-Surface-Id": "surf_demo",
            "X-App-Id": "app_demo",
            "Authorization": f"Bearer {token}",
        },
    )
    assert resp.status_code in {401, 403}
