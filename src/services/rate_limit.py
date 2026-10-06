"""Per-user sliding-window rate limiter (in memory)."""
from __future__ import annotations

import time
from collections import defaultdict, deque


class RateLimiter:
    def __init__(self, limit: int, window_sec: float = 60.0, clock=time.monotonic) -> None:
        self.limit = limit
        self.window = window_sec
        self._clock = clock
        self._hits: dict[int, deque[float]] = defaultdict(deque)

    def hit(self, user_id: int) -> bool:
        """Register a request. Returns False if the limit is exceeded (request not counted)."""
        now = self._clock()
        q = self._hits[user_id]
        while q and now - q[0] >= self.window:
            q.popleft()
        if len(q) >= self.limit:
            return False
        q.append(now)
        return True
