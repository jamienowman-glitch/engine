from engines.chat.contracts import Thread, Message, Contact


def test_contracts_create_defaults() -> None:
    contact = Contact(id="u1", display_name="User One")
    thread = Thread(id="t1", participants=[contact])
    msg = Message(id="m1", thread_id=thread.id, sender=contact, text="hi")
    assert thread.participants[0].id == "u1"
    assert msg.role == "user"
    assert msg.thread_id == "t1"
