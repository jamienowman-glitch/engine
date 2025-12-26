import pytest
from pathlib import Path

import engines.identity.auth as auth_module
from engines.identity.jwt_service import AuthContext
from engines.video_render.service import AssetAccessError, RenderService


def _default_video_render_auth():
    return AuthContext(
        user_id="lane2_render_user",
        email="lane2-render@example.com",
        tenant_ids=["t_test"],
        default_tenant_id="t_test",
        role_map={"t_test": "owner"},
    )


def _stub_get_auth_context(authorization: str | None = None) -> AuthContext:
    return _default_video_render_auth()


def _stub_ensure_local(self, uri: str) -> str:
    if uri.startswith("file://") or uri.startswith("/"):
        clean = uri.replace("file://", "")
        if "/non/existent" in clean:
            raise AssetAccessError(f"local asset not found: {uri}")
        path = Path(clean)
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"")
        return str(path)
    return uri


auth_module.get_auth_context = _stub_get_auth_context
RenderService._ensure_local = _stub_ensure_local


@pytest.fixture(autouse=True)
def _video_render_test_env(monkeypatch):
    monkeypatch.setenv("RAW_BUCKET", "test-raw-bucket")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_EC2_METADATA_DISABLED", "true")
    monkeypatch.setenv("DATASETS_BUCKET", "test-datasets-bucket")
    monkeypatch.setattr(auth_module, "get_auth_context", _stub_get_auth_context)
    monkeypatch.setattr(RenderService, "_ensure_local", _stub_ensure_local)
