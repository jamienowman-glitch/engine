import pytest
import json
from unittest.mock import MagicMock, patch
from engines.chat.contracts import Message, Contact, Thread
from engines.chat.service import redis_transport

@pytest.fixture
def mock_redis_module():
    with patch("engines.chat.service.redis_transport.redis") as mock:
        yield mock

@pytest.fixture
def mock_client(mock_redis_module):
    client = MagicMock()
    mock_redis_module.Redis.return_value = client
    # Default pubsub mock
    pubsub = MagicMock()
    pubsub.listen.return_value = []
    client.pubsub.return_value = pubsub
    return client

def test_redis_bus_init(mock_client):
    bus = redis_transport.RedisBus("host", 1234)
    assert bus.r == mock_client
    mock_client.pubsub.assert_called_once()

def test_create_thread(mock_client):
    bus = redis_transport.RedisBus("host", 1234)
    t = bus.create_thread(participants=[])
    
    mock_client.set.assert_called()
    mock_client.sadd.assert_called_with("threads", t.id)
    assert isinstance(t, Thread)

def test_add_message(mock_client):
    bus = redis_transport.RedisBus("host", 1234)
    msg = Message(id="m1", thread_id="t1", sender=Contact(id="u1"), text="hello")
    
    bus.add_message("t1", msg)
    
    # Check persistence
    args = mock_client.rpush.call_args
    assert args[0][0] == "thread:t1:messages"
    assert json.loads(args[0][1])["text"] == "hello"
    
    # Check pubsub
    mock_client.publish.assert_called_with("thread:t1", args[0][1])

def test_get_messages(mock_client):
    bus = redis_transport.RedisBus("host", 1234)
    msg = Message(id="m1", thread_id="t1", sender=Contact(id="u1"), text="hello")
    mock_client.lrange.return_value = [msg.json()]
    
    msgs = bus.get_messages("t1")
    assert len(msgs) == 1
    assert msgs[0].text == "hello"

def test_subscribe(mock_client):
    bus = redis_transport.RedisBus("host", 1234)
    cb = MagicMock()
    
    bus.subscribe("t1", cb)
    
    # Should subscribe to channel
    mock_client.pubsub.return_value.subscribe.assert_called_with("thread:t1")
