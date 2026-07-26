"""Authorization filter — the single gate for every admin handler.

Applied at the router level so no admin action can ever be reached without it
(fixing the old code, where admin callbacks had no authorization at all)."""

from __future__ import annotations

from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message, TelegramObject

from playnext.core.config import Settings


class IsAdmin(BaseFilter):
    async def __call__(self, event: TelegramObject, settings: Settings) -> bool:
        user = getattr(event, "from_user", None)
        return user is not None and settings.is_admin(user.id)


def actor_id(event: Message | CallbackQuery) -> int:
    assert event.from_user is not None
    return event.from_user.id
