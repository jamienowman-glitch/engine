from engines.guardrails.pii_text.engine import run
from engines.guardrails.pii_text.schemas import DataPolicyDecision, PiiTextRequest, PiiTextResult


def test_pii_text_masks_email_and_phone() -> None:
    req = PiiTextRequest(text="Email me at test@example.com or call +1 555-123-4567.")
    res = run(req)
    assert isinstance(res, PiiTextResult)
    assert isinstance(res.policy, DataPolicyDecision)
    assert "[REDACTED]" in res.clean_text
    assert "email" in res.pii_flags and "phone" in res.pii_flags
