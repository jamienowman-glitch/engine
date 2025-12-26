import pytest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from engines.common.identity import RequestContext, get_request_context
from engines.dataset.events.schemas import DatasetEvent
from engines.identity.auth import AuthContext, get_auth_context
from engines.logging.events import engine as logging_engine
from engines.privacy.routes import router as privacy_router
from engines.privacy.train_prefs import (
    InMemoryTrainingPreferenceRepository,
    TrainingPreferenceService,
    get_training_pref_service,
    set_training_pref_service,
)


app = FastAPI()
app.include_router(privacy_router)
client = TestClient(app)


def _request_context(role: str = "member", user_id: str = "u_test"):
    return RequestContext(tenant_id="t_privacy",
        env="dev",
        user_id=user_id,
        membership_role=role,
    )


def _auth_context(role: str = "member", user_id: str = "u_test"):
    return AuthContext(
        user_id=user_id,
        email="user@example.com",
        tenant_ids=["t_privacy"],
        default_tenant_id="t_privacy",
        role_map={"t_privacy": role},
    )


def _override_context(role: str = "member", user_id: str = "u_test"):
    app.dependency_overrides[get_request_context] = lambda: _request_context(role=role, user_id=user_id)
    app.dependency_overrides[get_auth_context] = lambda: _auth_context(role=role, user_id=user_id)


@pytest.fixture(autouse=True)
def reset_service_and_deps():
    app.dependency_overrides = {}
    set_training_pref_service(TrainingPreferenceService())


def test_user_opt_out_overrides_default() -> None:
    repo = InMemoryTrainingPreferenceRepository()
    svc = TrainingPreferenceService(repo=repo)
    svc.set_user_opt_out("t_demo", "dev", "u1", True)
    assert svc.train_ok("t_demo", "dev", "u1", default_ok=True) is False


def test_tenant_opt_out_blocks_when_no_user_pref() -> None:
    repo = InMemoryTrainingPreferenceRepository()
    svc = TrainingPreferenceService(repo=repo)
    svc.set_tenant_opt_out("t_demo", "dev", True)
    assert svc.train_ok("t_demo", "dev", None, default_ok=True) is False
    assert svc.train_ok("t_demo", "dev", "u2", default_ok=True) is False


def test_user_opt_in_overrides_tenant_opt_out() -> None:
    repo = InMemoryTrainingPreferenceRepository()
    svc = TrainingPreferenceService(repo=repo)
    svc.set_tenant_opt_out("t_demo", "dev", True)
    svc.set_user_opt_out("t_demo", "dev", "u1", False)
    assert svc.train_ok("t_demo", "dev", "u1", default_ok=True) is True


def test_tenant_opt_out_requires_admin() -> None:
    _override_context(role="viewer")
    response = client.post("/privacy/train-prefs/tenant", json={"opt_out": True})
    assert response.status_code == 403


def test_tenant_opt_out_accepts_owner() -> None:
    _override_context(role="owner")
    response = client.post("/privacy/train-prefs/tenant", json={"opt_out": True})
    assert response.status_code == 200
    prefs = get_training_pref_service().prefs_snapshot("t_privacy", "dev")
    assert prefs and prefs[0].opt_out is True


def test_user_opt_out_validated() -> None:
    _override_context(role="member", user_id="u_member")
    response = client.post("/privacy/train-prefs/user", json={"user_id": "u_other", "opt_out": True})
    assert response.status_code == 403


def test_user_opt_out_allows_self() -> None:
    _override_context(role="member", user_id="u_member")
    response = client.post("/privacy/train-prefs/user", json={"user_id": "u_member", "opt_out": True})
    assert response.status_code == 200


def test_logging_respects_preferences(monkeypatch) -> None:
    svc = TrainingPreferenceService()
    svc.set_user_opt_out("t_privacy", "dev", "u_member", True)
    set_training_pref_service(svc)

    class _StubPolicy:
        def __init__(self):
            self.train_ok = True
            self.reason = "ok"

    class _StubPiiResult:
        def __init__(self):
            self.pii_flags = []
            self.policy = _StubPolicy()

    monkeypatch.setattr(logging_engine, "pii_strip", lambda req: _StubPiiResult())
    monkeypatch.setattr(
        logging_engine,
        "get_backend",
        lambda client=None: type("Backend", (), {"write_event": lambda self, event: None})(),
    )

    event = DatasetEvent(
        tenantId="t_privacy",
        env="dev",
        surface="privacy",
        agentId="u_member",
        input={},
        output={},
        metadata={},
        analytics_event_type="audit",
        analytics_platform="internal",
    )
    result = logging_engine.run(event)
    assert result["status"] == "accepted"
    assert event.train_ok is False
