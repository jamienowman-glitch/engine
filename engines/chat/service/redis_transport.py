import json
import uuid
import logging
from typing import List, Callable, Any, Dict, Tuple

try:
    import redis
except ImportError:
    redis = None

from engines.chat.contracts import Message, Thread, Contact

logger = logging.getLogger(__name__)

class RedisBus:
    def __init__(self, host="localhost", port=6379, db=0):
        if not redis:
            raise RuntimeError("redis package is not installed")
        # Retry connection logic could be added here
        self.r = redis.Redis(host=host, port=port, db=db, decode_responses=True)
        self.subs: Dict[str, Tuple[Any, Any]] = {}  # sub_id -> (thread, pubsub)

    def create_thread(self, participants: List[Contact]) -> Thread:
        thread_id = uuid.uuid4().hex
        thread = Thread(id=thread_id, participants=participants)
        self.r.set(f"thread:{thread_id}", thread.json())
        return thread

    def list_threads(self) -> List[Thread]:
        # Performance warning: keys * is bad in prod, using SCAN is better but minimal scope
        keys = self.r.keys("thread:*")
        threads = []
        if keys:
            # MGET is faster
            values = self.r.mget(keys)
            for v in values:
                if v:
                    try:
                        threads.append(Thread.parse_raw(v))
                    except Exception as e:
                        logger.error(f"Failed to parse thread: {e}")
        return threads

    def add_message(self, thread_id: str, msg: Message) -> None:
        key = f"messages:{thread_id}"
        channel = f"channel:{thread_id}"
        payload = msg.json()
        
        # Atomic push + publish ideally, but independent is fine for this scope
        self.r.rpush(key, payload)
        self.r.publish(channel, payload)

    def get_messages(self, thread_id: str, after_id: str | None = None) -> List[Message]:
        key = f"messages:{thread_id}"
        # Fetch all. Optimization: store IDs in ZSET for range queries?
        # Scope: minimal. Just Fetch all and filter like InMemoryBus.
        raw_list = self.r.lrange(key, 0, -1)
        msgs = []
        for r in raw_list:
            try:
                msgs.append(Message.parse_raw(r))
            except Exception:
                continue
                
        if not after_id:
            return msgs
            
        for i, m in enumerate(msgs):
            if m.id == after_id:
                return msgs[i+1:]
        return []

    def subscribe(self, thread_id: str, callback: Callable[[Message], Any]) -> str:
        sub_id = uuid.uuid4().hex
        p = self.r.pubsub()
        
        def handler(message):
            # message is {'type': 'message', 'pattern': None, 'channel': '...', 'data': '...'}
            if message['type'] == 'message':
                try:
                    data = message['data']
                    msg = Message.parse_raw(data)
                    callback(msg)
                except Exception as e:
                    logger.error(f"Redis sub error: {e}")

        p.subscribe(**{f"channel:{thread_id}": handler})
        
        # run_in_thread from redis-py
        thread = p.run_in_thread(sleep_time=0.01, daemon=True)
        self.subs[sub_id] = (thread, p)
        return sub_id

    def unsubscribe(self, thread_id: str, sub_id: str) -> None:
        if sub_id in self.subs:
            thread, p = self.subs[sub_id]
            try:
                thread.stop()
                p.close()
            except Exception as e:
                logger.warning(f"Error unsubscribing redis: {e}")
            del self.subs[sub_id]
