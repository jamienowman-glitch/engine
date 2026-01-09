import pytest
from engines.common.identity import RequestContext
from engines.security.sanitizer import get_sanitizer
from engines.security.token_vault import get_token_vault

def test_pii_sanitization_and_rehydration():
    # 1. Setup
    ctx = RequestContext(tenant_id="t_lab_pii", env="dev", mode="lab", user_id="u1")
    sanitizer = get_sanitizer()
    vault = get_token_vault()
    
    # 2. Simulate Connector Output with PII
    raw_data = {
        "order_id": 123,
        "customer": {
            "email": "jay@example.com",
            "phone": "555-555-0199",
            "note": "Contact me at jay@example.com please"
        }
    }
    
    # 3. Sanitize
    clean_data = sanitizer.sanitize(ctx, raw_data)
    
    print(f"Clean Data: {clean_data}")
    
    # Verify Redaction
    assert clean_data["customer"]["email"] != "jay@example.com"
    assert clean_data["customer"]["email"].startswith("<PII_EMAIL_")
    
    assert clean_data["customer"]["phone"] != "555-555-0199"
    assert clean_data["customer"]["phone"].startswith("<PII_PHONE_")
    
    # Verify embedded redaction
    assert "jay@example.com" not in clean_data["customer"]["note"]
    assert "<PII_EMAIL_" in clean_data["customer"]["note"]

    # 4. Rehydrate
    token = clean_data["customer"]["email"]
    original = vault.retrieve(ctx.tenant_id, token)
    
    assert original == "jay@example.com"
    
    # Verify Tenant Isolation
    assert vault.retrieve("t_other", token) is None
