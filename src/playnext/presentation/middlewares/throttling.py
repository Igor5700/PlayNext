"""Lightweight per-user rate limiting (in-memory sliding minimum interval).

Protects against button-spam and accidental double taps. For a single-process
deployment this in-memory guard is sufficient; a Redis-backed variant can be
dropped in behind the same interface for horizontal scaling.
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, TelegramObject

_MIN_INTERVAL = 0.35  # seconds between accepted events per user


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, min_interval: float = _MIN_INTERVAL) -> None:
        self._min_interval = min_interval
        self._last: dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        tg_user = getattr(event, "from_user", None)
        if tg_user is None:
            return await handler(event, data)

        now = time.monotonic()
        last = self._last.get(tg_user.id, 0.0)
        if now - last < self._min_interval:
            if isinstance(event, CallbackQuery):
                await event.answer()  # silently ack, drop the action
            return None
        self._last[tg_user.id] = now

        # Opportunistically evict stale entries to bound memory.
        if len(self._last) > 10_000:
            cutoff = now - 60
            self._last = {uid: ts for uid, ts in self._last.items() if ts > cutoff}

        return await handler(event, data)
