from __future__ import annotations
import uuid
import time
from typing import Dict, Optional, Tuple
from threading import Lock

class TokenVault:
    """
    Secure storage for mapping PII values to tokens.
    Currently backed by in-memory dictionary.
    
    Structure:
    {
        tenant_id: {
            token: {
                "value": "original_email@example.com",
                "kind": "email",
                "created_at": timestamp
            }
        }
    }
    """
    _instance = None
    _lock = Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(TokenVault, cls).__new__(cls)
                    cls._instance._store = {} # type: Dict[str, Dict[str, Dict]]
        return cls._instance

    def store(self, tenant_id: str, value: str, kind: str = "generic") -> str:
        """
        Stores a value and returns a deterministic token.
        If existing value found for tenant, returns existing token to maintain consistency in a run.
        (Actually, for simplicity, we might generate new per run, but here we just map Value -> Token?)
        
        To be truly safe/stateless between runs, we might want random tokens.
        But for now, let's just make a new random token.
        """
        # Ensure tenant store exists
        if tenant_id not in self._store:
            self._store[tenant_id] = {} # token -> data
        
        # Check if value already exists? 
        # For simplicity/performance, skipping reverse lookup for now. 
        # Just generate new token.
        
        token_id = str(uuid.uuid4())[:8]
        token = f"<PII_{kind.upper()}_{token_id}>"
        
        self._store[tenant_id][token] = {
            "value": value,
            "kind": kind,
            "created_at": time.time()
        }
        
        return token

    def retrieve(self, tenant_id: str, token: str) -> Optional[str]:
        """
        Retrieves the original value for a token.
        Returns None if not found or tenant mismatch.
        """
        if tenant_id not in self._store:
            return None
            
        data = self._store[tenant_id].get(token)
        if data:
            return data["value"]
        return None

def get_token_vault() -> TokenVault:
    return TokenVault()
