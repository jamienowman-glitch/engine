from typing import Any
from fastapi import HTTPException
from engines.common.identity import RequestContext

class MissingChatStoreRoute(Exception):
    pass

def chat_store_or_503(context: RequestContext) -> Any:
    # Minimal mock for testing connectivity
    # In real world this would use routing registry
    return MockChatStore()

class MockChatStore:
    def get_thread(self, *args, **kwargs):
        return None
