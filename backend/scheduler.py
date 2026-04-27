from __future__ import annotations

import asyncio
from contextlib import suppress
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .news import get_app_config, get_refresh_status, refresh_items, write_refresh_status


class RefreshScheduler:
    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self._lock = asyncio.Lock()
        self._stopped = asyncio.Event()

    def start(self) -> None:
        if self._task and not self._task.done():
            return
        write_refresh_status({"running": False})
        self._stopped.clear()
        self._task = asyncio.create_task(self._run(), name="refresh-scheduler")

    async def stop(self) -> None:
        self._stopped.set()
        if self._task:
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task

    async def run_refresh(self, trigger: str = "manual") -> dict:
        async with self._lock:
            return await refresh_items(trigger=trigger)

    async def _run(self) -> None:
        while not self._stopped.is_set():
            try:
                await self._tick()
            except Exception as exc:
                write_refresh_status({"running": False, "last_error": {"source": "scheduler", "error": str(exc)}})
            await asyncio.sleep(60)

    async def _tick(self) -> None:
        config = get_app_config()["scheduler"]
        if not config.get("enabled", True):
            return

        try:
            tz = ZoneInfo(config.get("timezone", "Asia/Shanghai"))
        except ZoneInfoNotFoundError:
            tz = ZoneInfo("UTC")

        now = datetime.now(tz)
        daily_times = config.get("daily_times", [])
        status = get_refresh_status()

        for scheduled_time in daily_times:
            try:
                hour, minute = [int(part) for part in scheduled_time.split(":", 1)]
            except ValueError:
                continue

            scheduled_at = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            run_key = f"{scheduled_at.date().isoformat()} {scheduled_time}"
            delay_seconds = (now - scheduled_at).total_seconds()
            if delay_seconds < 0 or delay_seconds >= 60 or status.get("last_scheduled_key") == run_key:
                continue

            async with self._lock:
                latest_status = get_refresh_status()
                if latest_status.get("last_scheduled_key") == run_key:
                    return
                write_refresh_status({"last_scheduled_key": run_key})
                await refresh_items(trigger="scheduled")
            return


scheduler = RefreshScheduler()
