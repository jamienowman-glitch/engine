"""Logging engine with PII strip + Nexus persistence."""
from __future__ import annotations

import json
import sys

from engines.dataset.events.schemas import DatasetEvent
from engines.guardrails.pii_text.engine import run as pii_strip
from engines.guardrails.pii_text.schemas import PiiTextRequest
from engines.nexus.backends import get_backend


def run(event: DatasetEvent) -> dict:
    # 1) Strip PII
    text_fields = []
    for bucket in (event.input, event.output, event.metadata):
        for val in bucket.values():
            if isinstance(val, str):
                text_fields.append(val)
    combined = " ".join(text_fields)
    pii_result = pii_strip(PiiTextRequest(text=combined))
    event.pii_flags = {"pii_flags": pii_result.pii_flags}

    # 2) Persist to Nexus backend
    backend = get_backend()
    backend.write_event(event)

    # 3) Emit structured stdout for quick inspection
    sys.stdout.write(json.dumps({"tenantId": event.tenantId, "event": event.dict()}) + "\n")
    return {"status": "accepted", "tenantId": event.tenantId, "pii_flags": pii_result.pii_flags}
