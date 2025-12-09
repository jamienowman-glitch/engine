"""Lightweight EventLog entry helper reused across services."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from engines.config import runtime_config
from engines.dataset.events.schemas import DatasetEvent
from engines.logging.events.engine import run as log_dataset_event


class EventLogEntry(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: str
    asset_type: str
    asset_id: str
    tenant_id: str = Field(..., pattern=r"^t_[a-z0-9_-]+$")
    user_id: Optional[str] = None
    origin_ref: Dict[str, Any] = Field(default_factory=dict)
    episode_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)
    surface: str = "event"


EventLogger = Callable[[EventLogEntry], None]


def default_event_logger(entry: EventLogEntry) -> None:
    """Map EventLogEntry into the existing DatasetEvent pipeline."""
    env = runtime_config.get_env() or "dev"
    tenant_id = entry.tenant_id
    agent_id = entry.user_id or "system"
    metadata = dict(entry.metadata)
    metadata.update(
        {
            "event_type": entry.event_type,
            "asset_type": entry.asset_type,
            "asset_id": entry.asset_id,
            "origin_ref": entry.origin_ref,
            "episode_id": entry.episode_id,
        }
    )
    event = DatasetEvent(
        tenantId=tenant_id,
        env=env,
        surface=entry.surface,
        agentId=agent_id,
        input={"event_type": entry.event_type, "asset_type": entry.asset_type, "origin_ref": entry.origin_ref},
        output={"asset_id": entry.asset_id},
        metadata=metadata,
    )
    try:
        log_dataset_event(event)
    except Exception:
        # Best-effort logging; avoid failing caller paths in environments without connectors.
        return
