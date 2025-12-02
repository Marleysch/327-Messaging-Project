import threading

class LamportClock:
    def __init__(self, node_id: str):
        self._time = 0
        self._lock = threading.Lock()
        self.node_id = node_id

    def tick(self) -> int:
        with self._lock:
            self._time += 1
            return self._time

    def update(self, received_time: int) -> int:
        with self._lock:
            self._time = max(self._time, received_time) + 1
            return self._time

    def now(self) -> int:
        with self._lock:
            return self._time
