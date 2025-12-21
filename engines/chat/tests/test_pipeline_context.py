import pytest

from engines.chat.pipeline import _resolve_identity
from engines.common.identity import RequestContext
from engines.config import runtime_config


def test_resolve_identity_prefers_context():
    ctx = RequestContext(tenant_id="t_ctx", env="prod", request_id="req-ctx")
    tenant_id, env, request_id = _resolve_identity(ctx)
    assert tenant_id == "t_ctx"
    assert env == "prod"
    assert request_id == "req-ctx"


def test_resolve_identity_rejects_missing_tenant_in_prod(monkeypatch):
    monkeypatch.setattr(runtime_config, "get_env", lambda: "prod")
    monkeypatch.setattr(runtime_config, "get_tenant_id", lambda: None)
    with pytest.raises(RuntimeError):
        _resolve_identity(None)
