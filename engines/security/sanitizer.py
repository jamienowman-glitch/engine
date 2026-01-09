from __future__ import annotations
import re
from typing import Any, Dict, List, Union
from engines.common.identity import RequestContext
from engines.security.token_vault import get_token_vault

# Regex Patterns
EMAIL_REGEX = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
PHONE_REGEX = r'\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'

# Compilation
EMAIL_PATTERN = re.compile(EMAIL_REGEX)
PHONE_PATTERN = re.compile(PHONE_REGEX)

class DataSanitizer:
    """
    Sanitizes data structures by stripping PII and replacing with tokens.
    """
    
    def __init__(self):
        self.vault = get_token_vault()

    def sanitize(self, ctx: RequestContext, data: Any) -> Any:
        """
        Recursively sanitizes input data.
        Returns a new copy of data with PII replaced.
        """
        # Primitive types
        if isinstance(data, str):
            return self._sanitize_string(ctx.tenant_id, data)
        elif isinstance(data, (int, float, bool, type(None))):
            return data
            
        # Composite types
        elif isinstance(data, dict):
            new_dict = {}
            for k, v in data.items():
                # Heuristic: keys like "email" or "phone" often contain PII
                if self._is_sensitive_key(k):
                    # Force sanitization of value even if strict format check fails?
                    # For now, let's treat values normally, but maybe prioritize check.
                    pass
                new_dict[k] = self.sanitize(ctx, v)
            return new_dict
            
        elif isinstance(data, list):
            return [self.sanitize(ctx, item) for item in data]
            
        return data

    def _sanitize_string(self, tenant_id: str, text: str) -> str:
        # 1. Email Redaction
        # Find all emails
        # This naive replace works for discrete emails. Embedded in text is harder.
        # Let's assume values are mostly discrete fields for now (connector data).
        
        matches = EMAIL_PATTERN.findall(text)
        for match in matches:
            token = self.vault.store(tenant_id, match, kind="email")
            text = text.replace(match, token)
            
        matches = PHONE_PATTERN.findall(text)
        for match in matches:
             token = self.vault.store(tenant_id, match, kind="phone")
             text = text.replace(match, token)
             
        return text

    def _is_sensitive_key(self, key: str) -> bool:
        key = key.lower()
        return "email" in key or "phone" in key or "address" in key

_sanitizer_instance = DataSanitizer()
def get_sanitizer() -> DataSanitizer:
    return _sanitizer_instance
