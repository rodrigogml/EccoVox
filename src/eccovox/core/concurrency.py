"""Small deterministic concurrency guard for local runtime capacities."""

from __future__ import annotations

import threading
from contextlib import contextmanager
from collections.abc import Iterator

from eccovox.core.errors import EccoVoxError, ErrorCodeEnum


class CapacityLimiter:
    """Semaphore-backed limiter that rejects excess work when no slot is immediately available."""

    def __init__(self, max_concurrent: int, queue_size: int = 0) -> None:
        self._semaphore = threading.BoundedSemaphore(max_concurrent + queue_size)

    @contextmanager
    def acquire(self) -> Iterator[None]:
        """Acquire a capacity slot or raise a stable functional error."""

        acquired = self._semaphore.acquire(blocking=False)
        if not acquired:
            raise EccoVoxError(ErrorCodeEnum.CAPACITY_EXCEEDED, "Runtime capacity was exceeded.")
        try:
            yield
        finally:
            self._semaphore.release()
