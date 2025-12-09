"""Chat processing pipeline entrypoint (production wiring)."""
from __future__ import annotations

from typing import Iterable, List, Callable, Optional

from engines.chat.contracts import Contact, Message, ChatScope
from engines.chat.service.transport_layer import bus, publish_message
from engines.config import runtime_config
from engines.dataset.events.schemas import DatasetEvent
from engines.logging.events.engine import run as log_event
from engines.nexus.backends import get_backend
from engines.nexus.schemas import NexusDocument, NexusKind
from engines.chat.service import llm_client


def process_message(
    thread_id: str,
    sender: Contact,
    text: str,
    scope: ChatScope | None = None,
    stream_fn: Optional[Callable[..., Iterable[str]]] = None,
) -> List[Message]:
    """Persist the incoming message, log it, and emit an LLM-backed agent response."""
    tenant_id = runtime_config.get_tenant_id() or "t_unknown"
    env = runtime_config.get_env() or "dev"
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
    event = DatasetEvent(
        tenantId=tenant_id,
        env=env,
        surface="chat",
        agentId=sender.id,
        input={"text": text, "scope": scope.dict(exclude_none=True) if scope else None},
        output={},
        metadata={"kind": "chat_message"},
    )
    log_event(event)

    user_msg = publish_message(thread_id, sender, text, role="user", scope=scope)

    # Invoke LLM stream (Vertex/ADK) via client helper
    history = [{"role": m.role, "content": m.text} for m in bus.get_messages(thread_id)]
    stream_callable = stream_fn or llm_client.stream_chat
    agent_text_parts: List[str] = []
    for token in stream_callable(
        messages=history,
        tenant_id=tenant_id,
        thread_id=thread_id,
        scope=scope.dict(exclude_none=True) if scope else None,
    ):
        agent_text_parts.append(token)
    agent_text = "".join(agent_text_parts) if agent_text_parts else "[no-response]"

    agent = Contact(id="agent-orchestrator", display_name="Orchestrator")
    agent_msg = publish_message(thread_id, agent, agent_text, role="agent", scope=scope)
    return [user_msg, agent_msg]
