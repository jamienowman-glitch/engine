import pytest
from pydantic import ValidationError

from engines.chat.service.types import ChatControls, ChatMessageIn, ChatMessageOut, Env


def test_chat_message_in_validation() -> None:
    msg = ChatMessageIn(
        tenantId="t_demo",
        env=Env.dev,
        surface="web",
        conversationId="c1",
        messageId="m1",
        message="hi",
        controls=ChatControls(temperatureBand="cool"),
    )
    assert msg.tenantId == "t_demo"


def test_chat_message_in_rejects_bad_tenant() -> None:
    with pytest.raises(ValidationError):
        ChatMessageIn(
            tenantId="demo",  # missing prefix
            env=Env.dev,
            surface="web",
            conversationId="c1",
            messageId="m1",
            message="hi",
        )


def test_chat_message_out_defaults_state() -> None:
    out = ChatMessageOut(
        tenantId="t_demo",
        env=Env.dev,
        surface="web",
        conversationId="c1",
        messageId="m1",
        response="pong",
    )
    assert out.state.temperatureBand == "neutral"
    assert out.actions == []
