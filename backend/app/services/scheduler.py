"""Background jobs: subscriptions every minute (each at its own interval), clean-up rules hourly."""
import asyncio
import logging
import time

from . import cleanup, subscriptions

log = logging.getLogger("tubesy.scheduler")

TICK = 60
CLEANUP_EVERY = 3600


class Scheduler:
    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self._last_cleanup = 0.0

    async def tick(self) -> None:
        await subscriptions.check_due()
        if time.monotonic() - self._last_cleanup >= CLEANUP_EVERY:
            self._last_cleanup = time.monotonic()
            await cleanup.run_rules()

    async def _loop(self) -> None:
        await asyncio.sleep(10)  # let the queue start first
        while True:
            try:
                await self.tick()
            except Exception:
                log.exception("Hintergrundaufgabe fehlgeschlagen")
            await asyncio.sleep(TICK)

    def start(self) -> None:
        self._task = asyncio.create_task(self._loop())

    def stop(self) -> None:
        if self._task:
            self._task.cancel()


scheduler = Scheduler()
