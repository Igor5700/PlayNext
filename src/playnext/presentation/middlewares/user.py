"""Identity middleware: ensure the acting user exists and isn't blocked.

Injects the domain `User` into handler data so downstream handlers get identity
and balance without another query.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from playnext.application.ports.unit_of_work import UnitOfWorkFactory
from playnext.presentation import texts


class UserMiddleware(BaseMiddleware):
    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self._uow = uow_factory

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        tg_user = getattr(event, "from_user", None)
        if tg_user is None or tg_user.is_bot:
            return await handler(event, data)

        async with self._uow() as uow:
            user = await uow.users.get_or_create(
                tg_user.id,
                username=tg_user.username,
                first_name=tg_user.first_name or "",
            )
            await uow.commit()

        if user.is_blocked:
            if isinstance(event, CallbackQuery):
                await event.answer(texts.BLOCKED, show_alert=True)
            elif isinstance(event, Message):
                await event.answer(texts.BLOCKED)
            return None

        data["user"] = user
        return await handler(event, data)
