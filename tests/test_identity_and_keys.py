from __future__ import annotations

import os

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from engines.common.identity import RequestContext, get_request_context
from engines.common.keys import MissingKeyConfig, TenantKeySelector
from engines.common.secrets import SecretManagerClient, SecretNotFound
from engines.config import runtime_config
from engines.common import selecta
from engines.identity.models import TenantKeyConfig
from engines.identity.repository import InMemoryIdentityRepository


def _build_app():
    app = FastAPI()

    @app.get("/ctx")
    async def read_ctx(context: RequestContext = Depends(get_request_context)):
        return context.model_dump()

    @app.post("/ctx")
    async def read_ctx_post(context: RequestContext = Depends(get_request_context)):
        return context.model_dump()

    return app


def test_request_context_from_headers_and_body(monkeypatch):
    app = _build_app()
    client = TestClient(app)

    resp = client.get(
        "/ctx",
        headers={
            "X-Tenant-Id": "t_demo",
            "X-Mode": "saas",
            "X-Project-Id": "p_demo",
            "X-User-Id": "u1",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["tenant_id"] == "t_demo"
    assert data["mode"] == "saas"
    assert data["user_id"] == "u1"

    # fallback to body values when headers/query are absent
    resp = client.post(
        "/ctx",
        json={"tenant_id": "t_body", "mode": "saas", "project_id": "p_body", "user_id": "u2"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["tenant_id"] == "t_body"
    assert data["mode"] == "saas"
    assert data["user_id"] == "u2"


def test_assert_context_matches_env_mismatch():
    ctx = RequestContext(request_id="r", tenant_id="t_demo", mode="saas", project_id="p1")
    try:
        from engines.common.identity import assert_context_matches

        assert_context_matches(ctx, "t_demo", "enterprise")
    except Exception as exc:
        assert "mode mismatch" in str(exc)


class FakeSecretManager(SecretManagerClient):
    def __init__(self):
        super().__init__(client=self)
        self.storage = {}

    def access_secret(self, secret_id: str) -> str:
        if secret_id not in self.storage:
            raise SecretNotFound(secret_id)
        return self.storage[secret_id]

    def create_or_update_secret(self, secret_id: str, value: str) -> str:  # pragma: no cover - not used here
        self.storage[secret_id] = value
        return secret_id


def test_tenant_key_selector_with_fallback(monkeypatch):
    repo = InMemoryIdentityRepository()
    secrets = FakeSecretManager()
    selector = TenantKeySelector(repo, secret_client=secrets)

    # system slot as fallback
    repo.set_key_config(
        TenantKeyConfig(
            tenant_id="system",
            env="prod",
            slot="llm_primary",
            provider="openai",
            secret_name="system-llm-primary",
        )
    )
    secrets.storage["system-llm-primary"] = "sys-key"
    km = selector.get_config("t_demo", "prod", "llm_primary")
    assert km.secret == "sys-key"
    assert km.provider == "openai"

    # tenant-specific overrides system
    repo.set_key_config(
        TenantKeyConfig(
            tenant_id="t_demo",
            env="prod",
            slot="llm_primary",
            provider="openai",
            secret_name="tenant-llm",
        )
    )
    secrets.storage["tenant-llm"] = "tenant-key"
    km = selector.get_config("t_demo", "prod", "llm_primary")
    assert km.secret == "tenant-key"

    # missing config raises
    try:
        selector.get_config("t_other", "prod", "missing_slot")
    except MissingKeyConfig:
        pass
    else:  # pragma: no cover
        raise AssertionError("MissingKeyConfig not raised")


def test_key_selector_secret_missing_raises():
    repo = InMemoryIdentityRepository()
    secrets = FakeSecretManager()
    selector = TenantKeySelector(repo, secret_client=secrets)
    repo.set_key_config(
        TenantKeyConfig(
            tenant_id="t_demo",
            env="prod",
            slot="llm_primary",
            provider="openai",
            secret_name="missing-secret",
        )
    )
    try:
        selector.get_config("t_demo", "prod", "llm_primary")
    except SecretNotFound:
        pass
    else:  # pragma: no cover
        raise AssertionError("SecretNotFound not raised")


def test_runtime_config_prefers_selecta_metadata(monkeypatch):
    # Reset cached snapshot/resolver for isolation
    runtime_config.config_snapshot.cache_clear()  # type: ignore
    monkeypatch.setattr(selecta, "_default_resolver", None)

    monkeypatch.setenv("APP_ENV", "prod")
    monkeypatch.setenv("TENANT_ID", "t_test")
    for key in ("TEXT_EMBED_MODEL", "VECTOR_INDEX_ID", "VECTOR_ENDPOINT_ID", "VECTOR_PROJECT_ID"):
        monkeypatch.delenv(key, raising=False)

    repo = InMemoryIdentityRepository()
    secrets = FakeSecretManager()
    resolver = selecta.SelectaResolver(TenantKeySelector(repo, secret_client=secrets))
    selecta.set_selecta_resolver(resolver)

    repo.set_key_config(
        TenantKeyConfig(
            tenant_id="t_test",
            env="prod",
            slot="embed_primary",
            provider="vertex",
            secret_name="secret-text",
            metadata={"model_id": "meta-text"},
        )
    )
    secrets.storage["secret-text"] = "dummy"
    repo.set_key_config(
        TenantKeyConfig(
            tenant_id="t_test",
            env="prod",
            slot="vector_store_primary",
            provider="vertex",
            secret_name="secret-vector",
            metadata={"index_id": "idx-123", "endpoint_id": "ep-123", "project": "proj-123", "region": "us-test"},
        )
    )
    secrets.storage["secret-vector"] = "dummy"

    assert runtime_config.get_text_embedding_model_id() == "meta-text"
    assert runtime_config.get_vector_index_id() == "idx-123"
    assert runtime_config.get_vector_endpoint_id() == "ep-123"
    assert runtime_config.get_vector_project() == "proj-123"
    assert runtime_config.get_region() == "us-test"


def test_runtime_config_env_fallback_in_dev(monkeypatch):
    runtime_config.config_snapshot.cache_clear()  # type: ignore
    monkeypatch.setattr(selecta, "_default_resolver", None)
    monkeypatch.setenv("APP_ENV", "dev")
    monkeypatch.setenv("TENANT_ID", "t_test")
    monkeypatch.setenv("TEXT_EMBED_MODEL", "env-text")
    monkeypatch.setenv("VECTOR_INDEX_ID", "env-idx")
    monkeypatch.setenv("VECTOR_ENDPOINT_ID", "env-endpoint")
    monkeypatch.delenv("VECTOR_PROJECT_ID", raising=False)
    assert runtime_config.get_text_embedding_model_id() == "env-text"
    assert runtime_config.get_vector_index_id() == "env-idx"
    assert runtime_config.get_vector_endpoint_id() == "env-endpoint"


def test_selecta_vector_fallback_to_system(monkeypatch):
    repo = InMemoryIdentityRepository()
    secrets = FakeSecretManager()
    selector = TenantKeySelector(repo, secret_client=secrets)
    resolver = selecta.SelectaResolver(selector)
    selecta.set_selecta_resolver(resolver)
    repo.set_key_config(
        TenantKeyConfig(
            tenant_id="system",
            env="prod",
            slot="vector_store_primary",
            provider="vertex",
            secret_name="sys-vector",
            metadata={"index_id": "sys-idx", "endpoint_id": "sys-ep", "project": "sys-proj", "region": "us-central1"},
        )
    )
    secrets.storage["sys-vector"] = "ok"
    ctx = RequestContext(request_id="t", tenant_id="t_tenant", env="prod")
    cfg = resolver.vector_store_config(ctx)
    assert cfg.index_id == "sys-idx"
    assert cfg.endpoint_id == "sys-ep"
