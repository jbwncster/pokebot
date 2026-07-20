"""
Dead-simple process-wide rate limiter. Call wait() before any outbound
request to a source you want to be polite to (i.e. Serebii). Blocks the
calling thread until enough time has passed since the last call.
"""
import threading
import time


class RateLimiter:
    def __init__(self, min_interval_seconds: float):
        self.min_interval = min_interval_seconds
        self._lock = threading.Lock()
        self._last_call = 0.0

    def wait(self):
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_call
            if elapsed < self.min_interval:
                time.sleep(self.min_interval - elapsed)
            self._last_call = time.monotonic()
