from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Dict, Optional, List

from fastapi import HTTPException

from engines.canvas_commands.models import (
    CommandEnvelope,
    RevisionResult,
    CanvasSnapshot,
    CanvasReplayEvent,
)
from engines.canvas_commands.store_service import CanvasCommandStoreService
from engines.chat.contracts import Contact
from engines.chat.service.transport_layer import publish_message
from engines.common.identity import RequestContext
from engines.common.error_envelope import cursor_invalid_error
from engines.nexus.hardening.gate_chain import get_gate_chain
from engines.realtime.isolation import register_canvas_resource, verify_canvas_access

logger = logging.getLogger(__name__)


async def apply_command(
    tenant_id: str,
    user_id: str,
    command: CommandEnvelope,
    context: Optional[RequestContext] = None,
) -> RevisionResult:
    """
    Apply a command to a canvas strictly checking base_rev.
    """
    effective_tenant = context.tenant_id if context else tenant_id
    if context:
        register_canvas_resource(effective_tenant, command.canvas_id)

    verify_canvas_access(effective_tenant, command.canvas_id)

    if context:
        gate_chain = get_gate_chain()
        gate_chain.run(
            ctx=context,
            action="canvas_command",
            surface=context.surface_id or "canvas",
            subject_type="canvas",
            subject_id=command.canvas_id,
        )

        store = CanvasCommandStoreService(context)
    else:
        raise HTTPException(status_code=500, detail="RequestContext is required for persistence")

    current_rev = store.get_head_revision(command.canvas_id)

    if command.idempotency_key:
        existing = store.check_idempotency(command.canvas_id, command.idempotency_key)
        if existing:
            return RevisionResult(
                status="applied",
                current_rev=existing["revision"],
                your_rev=existing["revision"],
                event_id=existing["event_id"],
                reason="Idempotent replay",
            )

    if command.base_rev != current_rev:
        recovery_records = store.list_commands_since(command.canvas_id, command.base_rev)
        recovery_ops = [
            {
                "event_id": rec["event_id"],
                "type": rec["type"],
                "revision": rec["revision"],
            }
            for rec in recovery_records
        ]
        return RevisionResult(
            status="conflict",
            current_rev=current_rev,
            reason=f"Revision Mismatch: Expected {current_rev}, got {command.base_rev}",
            recovery_ops=recovery_ops,
        )

    record = store.append_command(
        canvas_id=command.canvas_id,
        command_id=command.id,
        idempotency_key=command.idempotency_key,
        base_rev=command.base_rev,
        command_type=command.type,
        command_args=command.args,
        user_id=user_id,
    )

    new_rev = record["revision"]
    event_id = record["event_id"]

    final_payload = {
        "kind": "canvas_commit",
        "cmd_id": command.id,
        "type": command.type,
        "rev": new_rev,
        "args": command.args,
        "event_id": event_id,
    }

    event_id_result = None
    msg = publish_message(
        command.canvas_id,
        Contact(id=user_id),
        json.dumps(final_payload),
        role="system",
        context=context,
    )
    event_id_result = msg.id

    return RevisionResult(
        status="applied",
        current_rev=new_rev,
        your_rev=new_rev,
        event_id=event_id_result,
    )


async def get_canvas_snapshot(
    canvas_id: str,
    tenant_id: str,
    context: Optional[RequestContext] = None,
) -> CanvasSnapshot:
    if not context:
        raise HTTPException(status_code=500, detail="RequestContext required")
    store = CanvasCommandStoreService(context)
    head_rev = store.get_head_revision(canvas_id)
    events = store.list_commands_since(canvas_id, 0)
    head_event_id = events[-1]["event_id"] if events else None
    timestamp = events[-1]["timestamp"] if events else None
    return CanvasSnapshot(
        canvas_id=canvas_id,
        head_rev=head_rev,
        state={},
        head_event_id=head_event_id,
        timestamp=timestamp,
    )


async def get_canvas_replay(
    canvas_id: str,
    tenant_id: str,
    after_event_id: Optional[str] = None,
    context: Optional[RequestContext] = None,
) -> List[CanvasReplayEvent]:
    if not context:
        raise HTTPException(status_code=500, detail="RequestContext required")
    store = CanvasCommandStoreService(context)
    events = store.list_commands_since(canvas_id, 0)

    start_index = 0
    if after_event_id:
        found_index = next(
            (idx for idx, evt in enumerate(events) if evt["event_id"] == after_event_id),
            None,
        )
        if found_index is None:
            raise cursor_invalid_error(after_event_id, domain="canvas")
        start_index = found_index + 1

    replay_events = events[start_index:]
    return [
        CanvasReplayEvent(
            event_id=evt["event_id"],
            type=evt["type"],
            revision=evt["revision"],
            command_id=evt.get("command_id"),
            data=evt.get("command_args", {}),
            timestamp=evt.get("timestamp"),
        )
        for evt in replay_events
    ]
