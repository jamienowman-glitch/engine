"""Vertex/ADK chat client helper.

Uses google-cloud-aiplatform if available; callers may monkeypatch stream_chat in tests.
"""
from __future__ import annotations

import os
from typing import Dict, Iterable, List, Optional

from engines.config import runtime_config
from engines.cost.vertex_guard import ensure_billable_vertex_allowed

try:  # pragma: no cover - import guarded for environments without Vertex libs
    from google.cloud import aiplatform  # type: ignore
except Exception:  # pragma: no cover
    aiplatform = None


def _client() -> Optional[object]:
    if aiplatform is None:
        return None
    project = runtime_config.get_firestore_project()
    location = runtime_config.get_region() or "us-central1"
    aiplatform.init(project=project, location=location)
    return aiplatform


def stream_chat(
    messages: List[Dict[str, str]],
    tenant_id: str,
    thread_id: str,
    scope: Optional[Dict[str, str]] = None,
) -> Iterable[str]:
    """Stream chat tokens from Vertex Gemini. Falls back to a clear error if unavailable."""
    ensure_billable_vertex_allowed("Vertex Gemini streaming")
    client = _client()
    if client is None:
        raise RuntimeError("Vertex AI client not available; install google-cloud-aiplatform")

    # Compose a simple prompt from history; in real prod this would use an agent manifest/blackboard.
    history_text = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
    meta = f"[tenant:{tenant_id} thread:{thread_id} scope:{scope}]" if scope else f"[tenant:{tenant_id} thread:{thread_id}]"
    prompt = f"{meta}\n{history_text}\nassistant:"

    model_name = os.getenv("VERTEX_MODEL", "gemini-1.5-flash-002")
    model = client.GenerativeModel(model_name)  # type: ignore[attr-defined]
    response = model.generate_content(prompt, stream=True)  # type: ignore[call-arg]
    for chunk in response:
        # chunk could be a GenerativeResponse with text attribute
        text = getattr(chunk, "text", None)
        if text:
            yield text
