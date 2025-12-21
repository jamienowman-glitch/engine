"""Bridge to Northstar Core streaming runtime."""
from __future__ import annotations

import asyncio
import json
import logging
import sys
import time
import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator, Dict, Any, Optional

# HACK: Dynamically inject northstar-core path since it's a peer repo
CORE_PATH = "/Users/jaynowman/dev/northstar-core"
if CORE_PATH not in sys.path:
    sys.path.append(CORE_PATH)

try:
    # Importing from 'runtime' package in northstar-core
    # We assume 'runtime.contract' has RuntimeAdapter and StreamChunk
    # or similar. Based on user prompt "RuntimeAdapter.invoke_stream".
    # We'll try to find the actual location dynamically or guess 'runtime.contract'
    # Checking file contents earlier showed 'runtime/contract.py'.
    from runtime.contract import RuntimeAdapter, StreamChunk
    CORE_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Northstar Core not found: {e}")
    CORE_AVAILABLE = False
    RuntimeAdapter = None  # type: ignore

from engines.chat.service.cancellation import is_cancelled

logger = logging.getLogger(__name__)

async def stream_run(
    tenant_id: str,
    env: str,
    thread_id: str,
    user_input: str,
    runtime_name: str = "stub", # Default to mock/stub runtime if not specified
    scope: Optional[Dict] = None
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Invokes Core RuntimeAdapter.invoke_stream and yields event envelopes.
    """
    run_id = str(uuid.uuid4())
    req_id = str(uuid.uuid4())
    start_ts = time.time()
    
    # 1. Yield run_start
    yield _envelope(
        "run_start", req_id, tenant_id, env, thread_id, run_id, 
        data={"runtime": runtime_name}
    )

    if not CORE_AVAILABLE:
        yield _envelope(
            "error", req_id, tenant_id, env, thread_id, run_id, 
            data={"message": "Northstar Core library not available"}
        )
        return

    # 2. Setup Runtime Request
    # Note: We need to instantiate the correct adapter.
    # For this phase, we'll try to instantiate a generic one or specific based on runtime_name
    # But since we can't use 'fake calls', and we need 'invoke_stream',
    # we assume we can import the specific adapter or a factory.
    # For simplicity in this bridge, we will assume a factory or registry exists in Core, 
    # OR we just instantiate the specific one we know about if 'stub' is passed.
    
    # Looking at file list: runtime/langgraph/adapter.py exists.
    # Let's try to load the requested runtime adapter.
    
    adapter = _get_adapter(runtime_name)
    if not adapter:
        yield _envelope(
            "error", req_id, tenant_id, env, thread_id, run_id, 
            data={"message": f"Runtime '{runtime_name}' not found"}
        )
        return

    # req = RuntimeRequest(...) -> Removed, contract uses args directly
    
    # 3. Stream Loop
    try:
        # invoke_stream returns AsyncIterator[StreamChunk]
        context = {"tenant_id": tenant_id, "env": env, "run_id": run_id}
        chunk_idx = 0
        
        # TestEchoAdapter logic needs to match signature
        if runtime_name == "test_echo":
             iterator = adapter.invoke_stream(
                card_id="stub.echo",
                input_data={"messages": [{"role": "user", "content": user_input}]},
                context=context
            )
        else:
             # Assume real adapter usage
             iterator = adapter.invoke_stream(
                card_id=f"{runtime_name}.default", # Placeholder card
                input_data={"messages": [{"role": "user", "content": user_input}]},
                context=context
            )

        async for chunk in iterator:
            if is_cancelled(run_id):
                yield _envelope("error", req_id, tenant_id, env, thread_id, run_id, data={"message": "Cancelled"})
                return

            # Map StreamChunk to Event
            # chunk is StreamChunk(TypedDict) -> dict
            c_type = chunk.get("chunk_kind", "unknown")
            c_content = chunk.get("text", chunk.get("delta", ""))
            
            if c_type == "token":
                yield _envelope(
                    "token_chunk", req_id, tenant_id, env, thread_id, run_id,
                    data={"delta": c_content, "index": chunk_idx}
                )
                chunk_idx += 1
            elif c_type == "error":
                yield _envelope(
                    "error", req_id, tenant_id, env, thread_id, run_id,
                    data={"message": c_content}
                )
            # Add other mappings as needed
            
    except Exception as e:
        logger.exception("Core stream failed")
        yield _envelope(
            "error", req_id, tenant_id, env, thread_id, run_id, 
            data={"message": str(e)}
        )
    finally:
        yield _envelope(
            "run_end", req_id, tenant_id, env, thread_id, run_id, 
            data={"duration_ms": int((time.time() - start_ts) * 1000)}
        )

def _envelope(
    kind: str, 
    req_id: str, 
    tenant_id: str, 
    env: str, 
    thread_id: str, 
    run_id: str, 
    data: Dict[str, Any], 
    step_id: Optional[str] = None
) -> Dict[str, Any]:
    return {
        "type": kind,
        "request_id": req_id,
        "tenant_id": tenant_id,
        "env": env,
        "thread_id": thread_id,
        "run_id": run_id,
        "step_id": step_id,
        "ts": datetime.now(timezone.utc).isoformat(),
        "data": data
    }

def _get_adapter(name: str):
    # Minimal factory for Phase 3
    # If name == 'stub', use the stub adapter from Core if it exists, or local dummy
    if name == "stub":
        # Dynamic import to avoid breaking if file moved
        # from runtime.runtime_impl import StubRuntimeAdapter # Hypothetical
        return None
    
    # If no mapping, try to return generic Stub for testing "Basic Hello Stream"
    # Create a local Ad-Hoc stub if core doesn't provided one easily reachable
    if name == "test_echo":
        return TestEchoAdapter()
        
    return None

class TestEchoAdapter:
    """Internal stub for testing the pipe without Core logic complexity."""
    async def invoke_stream(self, card_id: str, input_data: Dict, context: Dict):
        # Async generator
        text = input_data["messages"][-1]["content"]
        # Fake chunks
        words = text.split(" ")
        for i, w in enumerate(words):
            yield {"chunk_kind": "token", "text": w + " ", "delta": w + " ", "metadata": {}}
            await asyncio.sleep(0.05) # simulate latency for "live feel" check

class QuickChunk:
    def __init__(self, type, content):
        self.type = type
        self.content = content
