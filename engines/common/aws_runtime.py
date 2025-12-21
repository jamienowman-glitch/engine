"""AWS runtime helpers for identity and lightweight billing probes."""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    import boto3  # type: ignore
    from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError  # type: ignore


class AWSCredentialsError(RuntimeError):
    pass


def _session(region: Optional[str] = None):
    try:
        import boto3  # type: ignore
    except Exception as exc:
        raise AWSCredentialsError("boto3_missing") from exc
    return boto3.Session(region_name=region or os.getenv("AWS_DEFAULT_REGION"))


def aws_identity() -> Dict[str, str]:
    """Return AWS identity via STS GetCallerIdentity."""
    try:
        from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError  # type: ignore
    except Exception as exc:
        raise AWSCredentialsError("boto3_missing") from exc
    try:
        sess = _session()
        sts = sess.client("sts")
        resp = sts.get_caller_identity()
        return {
            "account_id": resp.get("Account"),
            "arn": resp.get("Arn"),
            "user_id": resp.get("UserId"),
            "region": sess.region_name or os.getenv("AWS_DEFAULT_REGION") or "us-east-1",
        }
    except (NoCredentialsError, PartialCredentialsError) as exc:
        raise AWSCredentialsError("aws_credentials_missing") from exc
    except ClientError as exc:  # pragma: no cover - exercised via billing probe
        raise AWSCredentialsError(exc.response.get("Error", {}).get("Message", str(exc))) from exc
    except Exception as exc:  # pragma: no cover - narrow safety net
        raise AWSCredentialsError(str(exc)) from exc


def aws_healthcheck() -> Dict[str, object]:
    ident = aws_identity()
    return {"ok": True, "identity": ident}


def aws_billing_probe() -> Dict[str, object]:
    """Attempt minimal Cost Explorer read; return permissions info instead of raising."""
    try:
        from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError  # type: ignore
    except Exception as exc:
        return {"ok": False, "error": "boto3_missing", "exception": exc.__class__.__name__}
    since = datetime.now(timezone.utc) - timedelta(days=7)
    until = datetime.now(timezone.utc)
    try:
        ce = _session().client("ce")
        ce.get_cost_and_usage(
            TimePeriod={"Start": since.strftime("%Y-%m-%d"), "End": until.strftime("%Y-%m-%d")},
            Granularity="DAILY",
            Metrics=["UnblendedCost"],
            MaxResults=1,
        )
        return {"ok": True}
    except (NoCredentialsError, PartialCredentialsError) as exc:
        return {"ok": False, "error": "aws_credentials_missing", "exception": exc.__class__.__name__}
    except ClientError as exc:
        err = exc.response.get("Error", {})
        code = err.get("Code") or ""
        message = err.get("Message") or str(exc)
        missing = "ce:GetCostAndUsage" if "AccessDenied" in code or "AccessDenied" in message else None
        return {
            "ok": False,
            "error": "access_denied" if "AccessDenied" in code else "client_error",
            "exception": exc.__class__.__name__,
            "message": message,
            "missing_permission": missing,
        }
    except Exception as exc:  # pragma: no cover - unexpected cases
        return {"ok": False, "error": "unknown", "exception": exc.__class__.__name__, "message": str(exc)}
