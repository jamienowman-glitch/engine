import os
from unittest.mock import patch

import pytest

from engines.identity.ticket_service import (
    TICKET_TTL_SECONDS,
    TicketError,
    context_from_ticket,
    issue_ticket,
    validate_ticket,
)


def test_ticket_issue_and_validate():
    scope = {
        "tenant_id": "t_demo",
        "mode": "saas",
        "project_id": "p_chat",
        "request_id": "req-ticket",
        "user_id": "u_test",
    }
    with patch.dict(os.environ, {"ENGINES_TICKET_SECRET": "ticket-secret"}):
        token = issue_ticket(scope)
        payload = validate_ticket(token)
        assert payload["tenant_id"] == scope["tenant_id"]
        assert payload["mode"] == scope["mode"]
        assert payload["project_id"] == scope["project_id"]
        assert payload["exp"] - payload["iat"] == TICKET_TTL_SECONDS

        ctx = context_from_ticket(token)
        assert ctx.tenant_id == scope["tenant_id"]
        assert ctx.mode == scope["mode"]
        assert ctx.project_id == scope["project_id"]
        assert ctx.user_id == scope["user_id"]


def test_ticket_tamper_fails():
    scope = {"tenant_id": "t_demo", "mode": "saas", "project_id": "p_chat"}
    with patch.dict(os.environ, {"ENGINES_TICKET_SECRET": "ticket-secret"}):
        token = issue_ticket(scope)
        tampered = token + "extra"
        with pytest.raises(TicketError):
            validate_ticket(tampered)
