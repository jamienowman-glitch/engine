import os

import pytest

from engines.chat.service import transport_layer
from engines.chat.service.transport_layer import bus
from engines.identity import state as identity_state
from engines.identity.jwt_service import default_jwt_service
from engines.identity.models import TenantKeyConfig
from engines.realtime.isolation import registry


@pytest.fixture(autouse=True)
def identity_key_config():
    os.environ.setdefault("ENV", "dev")
    os.environ.setdefault("AUTH_JWT_SIGNING", "phase1-secret")
    config = TenantKeyConfig(
        tenant_id="system",
        env="prod",
        slot="auth_jwt_signing",
        provider="local",
        secret_name="auth_jwt_signing",
    )
    identity_state.identity_repo.set_key_config(config)
    yield
    identity_state.identity_repo._keys.clear()


@pytest.fixture(autouse=True)
def reset_stream_state():
    registry.clear()
    transport_layer.bus._impl = transport_layer.InMemoryBus()
    bus.messages.clear()
    bus.subscribers.clear()
    bus.threads.clear()
    yield
    registry.clear()
    bus.messages.clear()
    bus.subscribers.clear()
    bus.threads.clear()


@pytest.fixture
def jwt_issuer():
    def _issue(tenant_id: str = "t_alpha", user_id: str = "user-alpha"):
        svc = default_jwt_service()
        claims = {
            "sub": user_id,
            "email": f"{user_id}@example.com",
            "tenant_ids": [tenant_id],
            "default_tenant_id": tenant_id,
            "role_map": {tenant_id: "owner"},
        }
        return svc.issue_token(claims)

    return _issue
