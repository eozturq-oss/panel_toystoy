from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from time import monotonic
from typing import Any


@dataclass(order=True)
class QueueJob:
    priority: int
    sequence: int
    marketplace: str = field(compare=False)
    operation: Callable[[], Awaitable[Any]] = field(compare=False)
    attempts: int = field(default=0, compare=False)


class QueueManager:
    """Async FIFO/priority queue with per-marketplace rate limiting and retries."""

    def __init__(
        self,
        *,
        requests_per_minute: dict[str, int] | None = None,
        max_retries: int = 3,
    ) -> None:
        self.requests_per_minute = {key.upper(): value for key, value in (requests_per_minute or {}).items()}
        self.max_retries = max_retries
        self._queue: asyncio.PriorityQueue[QueueJob] = asyncio.PriorityQueue()
        self._next_sequence = 0
        self._next_allowed: dict[str, float] = {}

    async def enqueue(
        self,
        marketplace: str,
        operation: Callable[[], Awaitable[Any]],
        *,
        priority: int = 10,
    ) -> None:
        self._next_sequence += 1
        await self._queue.put(
            QueueJob(priority, self._next_sequence, marketplace.upper(), operation)
        )

    async def run_once(self) -> Any:
        """Process one queued request, retrying transient failures."""
        job = await self._queue.get()
        try:
            await self._wait_for_rate_limit(job.marketplace)
            while True:
                try:
                    result = await job.operation()
                    return result
                except Exception:
                    job.attempts += 1
                    if job.attempts > self.max_retries:
                        raise
                    await asyncio.sleep(min(2 ** job.attempts, 30))
        finally:
            self._queue.task_done()

    async def drain(self) -> list[Any]:
        results: list[Any] = []
        while not self._queue.empty():
            results.append(await self.run_once())
        return results

    def qsize(self) -> int:
        return self._queue.qsize()

    async def _wait_for_rate_limit(self, marketplace: str) -> None:
        limit = self.requests_per_minute.get(marketplace)
        if not limit or limit <= 0:
            return
        interval = 60 / limit
        now = monotonic()
        allowed_at = self._next_allowed.get(marketplace, now)
        if allowed_at > now:
            await asyncio.sleep(allowed_at - now)
        self._next_allowed[marketplace] = max(allowed_at, monotonic()) + interval
