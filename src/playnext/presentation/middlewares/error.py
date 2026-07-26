"""Centralised error handling.

Expected domain errors become friendly inline messages; unexpected ones are
logged with full context and surface a generic apology. Handlers never have to
wrap their bodies in try/except.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

import sentry_sdk
from aiogram import BaseMiddleware
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, Message, TelegramObject

from playnext.core.exceptions import PlayNextError
from playnext.presentation import texts

logger = logging.getLogger("playnext.errors")


class ErrorMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        try:
            return await handler(event, data)
        except PlayNextError as exc:
            await self._notify(event, exc.user_message)
        except TelegramBadRequest as exc:
            # Editing to an identical screen is benign; anything else is a real bug.
            if "not modified" not in str(exc).lower():
                logger.warning("Telegram API error: %s", exc)
        except Exception:
            logger.exception("Unhandled error while processing update")
            sentry_sdk.capture_exception()
            await self._notify(event, texts.GENERIC_ERROR)
        return None

    @staticmethod
    async def _notify(event: TelegramObject, message: str) -> None:
        try:
            if isinstance(event, CallbackQuery):
                await event.answer(message, show_alert=True)
            elif isinstance(event, Message):
                await event.answer(message)
        except TelegramBadRequest:
            pass
