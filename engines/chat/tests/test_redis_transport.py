import pytest
from unittest.mock import MagicMock, patch
from engines.chat.contracts import Message, Contact, Thread
from engines.chat.service.redis_transport import RedisBus

# Mock redis package if not installed, though our code checks for it.
# We assume the code imports 'redis'. If it's missing, RedisBus raises (if instantiated).
# We patch valid redis import.

@pytest.fixture
def mock_redis():
    # Patch where RedisBus imports it
    with patch("engines.chat.service.redis_transport.redis") as mock_pkg:
        # If redis is None in the module (ImportError), verify logic might fail or skip.
        # But we assume installed environment.
        mock_instance = MagicMock()
        mock_pkg.Redis.return_value = mock_instance
        yield mock_instance

def test_create_thread(mock_redis):
    bus = RedisBus()
    participants = [Contact(id="user1")]
    t = bus.create_thread(participants)
    
    assert isinstance(t, Thread)
    assert t.participants[0].id == "user1"
    
    # Verify Redis SET called
    mock_redis.set.assert_called_once()
    args = mock_redis.set.call_args[0]
    assert args[0] == f"thread:{t.id}"
    assert "user1" in args[1] # JSON payload

def test_add_message(mock_redis):
    bus = RedisBus()
    msg = Message(id="msg1", thread_id="t1", sender=Contact(id="u1"), text="hello")
    
    bus.add_message("t1", msg)
    
    # Verify RPUSH and PUBLISH
    mock_redis.rpush.assert_called_once()
    mock_redis.publish.assert_called_once()
    
    push_args = mock_redis.rpush.call_args[0]
    assert push_args[0] == "messages:t1"
    
    pub_args = mock_redis.publish.call_args[0]
    assert pub_args[0] == "channel:t1"

def test_subscribe_lifecycle(mock_redis):
    bus = RedisBus()
    pubsub_mock = MagicMock()
    mock_redis.pubsub.return_value = pubsub_mock
    thread_mock = MagicMock()
    pubsub_mock.run_in_thread.return_value = thread_mock
    
    callback = MagicMock()
    sub_id = bus.subscribe("t1", callback)
    
    assert sub_id
    mock_redis.pubsub.assert_called_once()
    pubsub_mock.subscribe.assert_called()
    # Arguments to subscribe are **kwargs, hard to inspect strictly without unpacking
    # But checks it was called.
    
    pubsub_mock.run_in_thread.assert_called()
    
    # Unsubscribe
    bus.unsubscribe("t1", sub_id)
    thread_mock.stop.assert_called()
    pubsub_mock.close.assert_called()

def test_get_messages(mock_redis):
    bus = RedisBus()
    # Mock lrange return
    msg1 = Message(id="1", thread_id="t1", sender=Contact(id="u1"), text="A")
    msg2 = Message(id="2", thread_id="t1", sender=Contact(id="u1"), text="B")
    
    mock_redis.lrange.return_value = [msg1.json(), msg2.json()]
    
    msgs = bus.get_messages("t1")
    assert len(msgs) == 2
    assert msgs[0].text == "A"
    
    # Test after_id
    msgs_after = bus.get_messages("t1", after_id="1")
    assert len(msgs_after) == 1
    assert msgs_after[0].text == "B"
