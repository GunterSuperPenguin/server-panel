import queue
import threading
from collections import deque


class Hub:
    def __init__(self):
        self.lock = threading.Lock()
        self.clients = []
        self.history = deque(maxlen=3000)
        self.state = "stopped"
        self.p2p = None

    def _state_msg(self):
        return {"type": "state", "state": self.state, "p2p": self.p2p}

    def _push(self, msg):
        for q in self.clients:
            q.put(msg)

    def log(self, text):
        with self.lock:
            self.history.append(text)
            self._push({"type": "line", "text": text})

    def set(self, state, p2p=None):
        with self.lock:
            self.state, self.p2p = state, p2p
            self._push(self._state_msg())

    def subscribe(self):
        q = queue.Queue()
        with self.lock:
            q.put(self._state_msg())
            q.put({"type": "history", "lines": list(self.history)})
            self.clients.append(q)
        return q

    def unsubscribe(self, q):
        with self.lock:
            if q in self.clients:
                self.clients.remove(q)
