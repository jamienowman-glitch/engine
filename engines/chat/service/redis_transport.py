import json
import threading
import uuid
import os
from typing import List, Dict, Callable, Tuple, Any, Optional

try:
    import redis
except ImportError:
    redis = None  # type: ignore

from engines.chat.contracts import Message, Thread, Contact

class RedisBus:
    def __init__(self, host: str, port: int, db: int = 0, password: Optional[str] = None):
        if not redis:
            raise ImportError("redis-py is required for RedisBus")
        self.r = redis.Redis(host=host, port=port, db=db, password=password, decode_responses=True)
        self.pubsub = self.r.pubsub()
        self.callbacks: Dict[str, Dict[str, Callable[[Message], Any]]] = {}  # thread_id -> {sub_id -> callback}
        self.lock = threading.Lock()
        self.listener_thread: Optional[threading.Thread] = None
        self._listening = False

    def _listener(self):
        self._listening = True
        try:
            for message in self.pubsub.listen():
                if not self._listening:
                    break
                if message['type'] == 'message':
                    channel = message['channel']
                    data = message['data']
                    try:
                        # channel is "thread:{id}"
                        thread_id = channel.split(":", 1)[1]
                        msg_dict = json.loads(data)
                        msg = Message(**msg_dict)
                        
                        subs = []
                        with self.lock:
                            if thread_id in self.callbacks:
                                subs = list(self.callbacks[thread_id].values())
                        
                        for cb in subs:
                            try:
                                cb(msg)
                            except Exception:
                                pass
                    except Exception as e:
                        print(f"RedisBus dispatch error: {e}")
        finally:
            self._listening = False

    def _ensure_listener(self):
        with self.lock:
            if not self.listener_thread or not self.listener_thread.is_alive():
                self.listener_thread = threading.Thread(target=self._listener, daemon=True)
                self.listener_thread.start()

    def create_thread(self, participants: List[Contact]) -> Thread:
        thread_id = uuid.uuid4().hex
        thread = Thread(id=thread_id, participants=participants)
        # Persist logic: store metadata
        self.r.set(f"thread:{thread_id}:meta", thread.json())
        self.r.sadd("threads", thread_id)
        return thread

    def list_threads(self) -> List[Thread]:
        thread_ids = self.r.smembers("threads")
        threads = []
        for tid in thread_ids:
            raw = self.r.get(f"thread:{tid}:meta")
            if raw:
                try:
                    threads.append(Thread(**json.loads(raw)))
                except:
                    pass
        return threads

    def add_message(self, thread_id: str, msg: Message) -> None:
        payload = msg.json()
        # 1. Store in list
        self.r.rpush(f"thread:{thread_id}:messages", payload)
        # 2. Publish
        self.r.publish(f"thread:{thread_id}", payload)

    def get_messages(self, thread_id: str, after_id: str | None = None) -> List[Message]:
        # Simple fetch all for now, or slice if optimized
        raw_list = self.r.lrange(f"thread:{thread_id}:messages", 0, -1)
        msgs = [Message(**json.loads(m)) for m in raw_list]
        
        if not after_id:
            return msgs
        
        # Seek
        try:
            for i, m in enumerate(msgs):
                if m.id == after_id:
                    return msgs[i+1:]
        except:
            pass
        return []

    def subscribe(self, thread_id: str, callback: Callable[[Message], Any]) -> str:
        with self.lock:
            setup_sub = (thread_id not in self.callbacks)
            if setup_sub:
                self.callbacks[thread_id] = {}
            
            sub_id = uuid.uuid4().hex
            self.callbacks[thread_id][sub_id] = callback
            
            if setup_sub:
                # Subscribe to redis channel
                self.pubsub.subscribe(f"thread:{thread_id}")
        
        self._ensure_listener()
        return sub_id

    def unsubscribe(self, thread_id: str, sub_id: str) -> None:
        with self.lock:
            if thread_id in self.callbacks:
                self.callbacks[thread_id].pop(sub_id, None)
                if not self.callbacks[thread_id]:
                    del self.callbacks[thread_id]
                    self.pubsub.unsubscribe(f"thread:{thread_id}")
