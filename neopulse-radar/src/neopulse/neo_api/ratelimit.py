"""Giới hạn tần suất phía client (token bucket) - NEO API cho tối đa 5 request/giây."""
from __future__ import annotations

import threading
import time
from collections.abc import Callable


class RateLimiter:
    """Token bucket an toàn đa luồng.

    `rate` request/giây, dồn tối đa `burst` request. `acquire()` chặn cho tới khi có lượt.
    Đồng hồ và hàm ngủ được tiêm vào để kiểm thử không cần chờ thật.
    """

    def __init__(self, rate: float, burst: int = 1, *,
                 clock: Callable[[], float] = time.monotonic,
                 sleep: Callable[[float], None] = time.sleep):
        if rate <= 0:
            raise ValueError("rate phải > 0")
        self.rate = float(rate)
        self.capacity = float(max(1, burst))
        self._tokens = self.capacity
        self._clock, self._sleep = clock, sleep
        self._last = clock()
        self._lock = threading.Lock()
        self.total_wait = 0.0

    def acquire(self) -> float:
        """Lấy 1 lượt; trả về số giây đã phải chờ."""
        waited = 0.0
        while True:
            with self._lock:
                now = self._clock()
                self._tokens = min(self.capacity, self._tokens + (now - self._last) * self.rate)
                self._last = now
                if self._tokens >= 1.0 - 1e-9:  # dung sai số thực: tránh ngủ lặp vô hạn với phần dư ~1e-17
                    self._tokens = max(0.0, self._tokens - 1.0)
                    self.total_wait += waited
                    return waited
                need = max((1.0 - self._tokens) / self.rate, 1e-6)
            self._sleep(need)
            waited += need
