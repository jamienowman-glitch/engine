"""Logging engine with PII strip + Nexus persistence."""
from __future__ import annotations

import json
import logging
import sys

from engines.dataset.events.schemas import DatasetEvent
from engines.guardrails.pii_text.engine import run as pii_strip
from engines.guardrails.pii_text.schemas import PiiTextRequest
from engines.nexus.backends import get_backend
from engines.privacy.train_prefs import get_training_pref_service

logger = logging.getLogger(__name__)


def run(event: DatasetEvent) -> dict:
    # 1) Strip PII
    text_fields = []
    for bucket in (event.input, event.output, event.metadata):
        for val in bucket.values():
            if isinstance(val, str):
                text_fields.append(val)
    combined = " ".join(text_fields)
    pii_result = pii_strip(PiiTextRequest(text=combined))
    event.pii_flags = {"flags": pii_result.pii_flags, "policy_reason": pii_result.policy.reason}

    # 1b) Compute train_ok (PII policy + tenant/user opt-out)
    pref_service = get_training_pref_service()
    event.train_ok = pref_service.train_ok(
        tenant_id=event.tenantId,
        env=event.mode or event.env,
        user_id=event.agentId,
        default_ok=pii_result.policy.train_ok,
    )

    # 2) Persist to Nexus backend
    backend = get_backend()
    try:
        backend.write_event(event)
    except Exception as exc:
        logger.warning("Nexus backend failed to persist event", exc_info=exc)
        return {"status": "error", "tenantId": event.tenantId, "error": str(exc)}

    # 3) Emit structured stdout for quick inspection
    sys.stdout.write(json.dumps({"tenantId": event.tenantId, "event": event.model_dump()}) + "\n")
    return {"status": "accepted", "tenantId": event.tenantId, "pii_flags": pii_result.pii_flags}
