"""Chat processing pipeline entrypoint (production wiring)."""
from __future__ import annotations

import uuid
from typing import Iterable, List, Callable, Optional

from engines.chat.contracts import Contact, Message, ChatScope
from engines.chat.service.transport_layer import bus, publish_message
from engines.config import runtime_config
from engines.dataset.events.schemas import DatasetEvent
from engines.logging.events.engine import run as log_event
from engines.nexus.backends import get_backend
from engines.nexus.schemas import NexusDocument, NexusKind
from engines.chat.service import llm_client
from engines.common.identity import RequestContext

PROD_ENVS = {"prod", "staging"}


def _resolve_identity(context: RequestContext | None) -> tuple[str, str, str, str, str, str, Optional[str]]:
    env_value = context.env if context else runtime_config.get_env() or "dev"
    env_normalized = env_value.lower()
    normalized_env = "staging" if env_normalized == "stage" else env_normalized
    tenant_id = context.tenant_id if context else runtime_config.get_tenant_id()
    if not tenant_id:
        if normalized_env in PROD_ENVS:
            raise RuntimeError("tenant_id required for chat events in prod")
        tenant_id = "t_unknown"
    request_id = context.request_id if context else uuid.uuid4().hex
    project_id = context.project_id if context else runtime_config._default_project_id()
    app_id = context.app_id if context else None
    surface_id = context.surface_id if context else None
    mode = normalized_env
    return tenant_id, normalized_env, mode, request_id, project_id, app_id, surface_id


async def process_message(
    thread_id: str,
    sender: Contact,
    text: str,
    scope: ChatScope | None = None,
    stream_fn: Optional[Callable[..., Iterable[str]]] = None,  # Legacy hook
    context: RequestContext | None = None,
) -> List[Message]:
    """Persist the incoming message, log it, and emit an LLM-backed agent response."""
    if context is None:
        raise RuntimeError("RequestContext is required for chat processing")
    (
        tenant_id,
        env,
        mode,
        request_id,
        project_id,
        app_id,
        context_surface_id,
    ) = _resolve_identity(context)
    backend = get_backend()

    # Persist snippet to Nexus
    tags = ["chat", sender.id]
    if scope:
        tags.extend(scope.tags())
    backend.write_snippet(
        NexusKind.data,
        NexusDocument(id=f"{thread_id}-{sender.id}", text=text),
        tags=tags,
    )

    # Log event (PII strip inside logging engine)
    surface_id = (
        scope.surface
        if scope and scope.surface
        else context_surface_id
        if context_surface_id
        else "chat"
    )
    event = DatasetEvent(
        tenantId=tenant_id,
        env=env,
        mode=mode,
        project_id=project_id,
        app_id=app_id,
        surface="chat",
        surface_id=surface_id,
        agentId=sender.id,
        input={"text": text, "scope": scope.dict(exclude_none=True) if scope else None},
        output={},
        metadata={"kind": "chat_message", "request_id": request_id},
        traceId=request_id,
        requestId=request_id,
        run_id=thread_id,
        step_id=request_id,
    )
    log_event(event)

    user_msg = publish_message(thread_id, sender, text, role="user", scope=scope, context=context)

    # Switch: Invoke Core Bridge (Async)
    from engines.chat.service import core_bridge
    import json
    import time
    
    agent = Contact(id="agent-orchestrator", display_name="Orchestrator")
    
    start_ts = time.time()
    ttfc_ms = 0
    chunk_count = 0
    
    # Use "test_echo" runtime for Phase 3 Verification if triggered with specific text
    # In real prod, we'd look up agent config from Nexus
    runtime_name = "test_echo" if "echo" in text.lower() else "stub"

    agent_text_parts: List[str] = []
    
    try:
        async for envelope in core_bridge.stream_run(
            tenant_id=tenant_id,
            env=env,
            thread_id=thread_id,
            user_input=text,
            runtime_name=runtime_name,
            scope=scope.dict(exclude_none=True) if scope else None
        ):
            # Capture TTFC
            if chunk_count == 0 and envelope["type"] == "token_chunk":
                ttfc_ms = int((time.time() - start_ts) * 1000)
            
            if envelope["type"] == "token_chunk":
                chunk_count += 1
                delta = envelope["data"].get("delta", "")
                agent_text_parts.append(delta)
            
            # Publish Envelope via Bus (serialized in text)
            # This allows UI to parse JSON and route events
            payload_str = json.dumps(envelope, default=str)
            publish_message(thread_id, agent, payload_str, role="agent", scope=scope)
            
        print(f"STREAM STATS: run_id={thread_id} ttfc_ms={ttfc_ms} in {int((time.time()-start_ts)*1000)}ms chunks={chunk_count}")

    except Exception as e:
        import traceback
        traceback.print_exc()
        err_payload = json.dumps({
            "type": "error", 
            "data": {"message": str(e)}
        })
        publish_message(thread_id, agent, err_payload, role="agent", scope=scope)

    agent_text = "".join(agent_text_parts) if agent_text_parts else "[no-response]"
    # Final 'clean' message persistence could happen here if we wanted a consolidated record
    # But for stream, we emit chunks.
    
    # We return the "final" message object constructed from parts for callers who wait (HTTP)
    # But HTTP callers currently wait for list.
    final_msg = Message(
        id=f"final-{thread_id}", 
        thread_id=thread_id, 
        sender=agent, 
        text=agent_text, 
        role="agent"
    )
    return [user_msg, final_msg]
