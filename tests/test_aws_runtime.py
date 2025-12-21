from __future__ import annotations

import pytest

try:
    from botocore.exceptions import ClientError  # type: ignore
except Exception:  # pragma: no cover - boto3 not installed
    ClientError = None  # type: ignore

from engines.common import aws_runtime


class _DummySTS:
    def get_caller_identity(self):
        return {"Account": "123456789012", "Arn": "arn:aws:iam::123:user/demo", "UserId": "AID123"}


class _DummyCE:
    def __init__(self, should_deny: bool = False):
        self.should_deny = should_deny

    def get_cost_and_usage(self, **kwargs):
        if self.should_deny:
            raise ClientError(
                error_response={"Error": {"Code": "AccessDeniedException", "Message": "User is not authorized to perform ce:GetCostAndUsage"}},
                operation_name="GetCostAndUsage",
            )
        return {"ResultsByTime": []}


class _DummySession:
    def __init__(self, deny_cost: bool = False):
        self.region_name = "us-east-1"
        self._deny_cost = deny_cost

    def client(self, name, **kwargs):
        if name == "sts":
            return _DummySTS()
        if name == "ce":
            return _DummyCE(should_deny=self._deny_cost)
        raise ValueError(name)


def test_aws_identity(monkeypatch):
    if ClientError is None:
        pytest.skip("boto3 not installed")
    monkeypatch.setattr(aws_runtime, "_session", lambda region=None: _DummySession())
    ident = aws_runtime.aws_identity()
    assert ident["account_id"] == "123456789012"
    assert ident["arn"].startswith("arn:aws")


def test_aws_billing_probe_access_denied(monkeypatch):
    if ClientError is None:
        pytest.skip("boto3 not installed")
    monkeypatch.setattr(aws_runtime, "_session", lambda region=None: _DummySession(deny_cost=True))
    result = aws_runtime.aws_billing_probe()
    assert result["ok"] is False
    assert result["missing_permission"] == "ce:GetCostAndUsage"
