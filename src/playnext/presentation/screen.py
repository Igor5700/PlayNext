"""Single-message screen renderer.

The bot maintains one "live" message and updates it in place — the core of the
app-like feel. This helper hides the messy details of Telegram's edit API:
text↔media transitions, "message is not modified" noise, and graceful fallbacks.
"""

from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardMarkup,
    InputFile,
    InputMediaPhoto,
    Message,
)


@dataclass(frozen=True, slots=True)
class Screen:
    text: str
    markup: InlineKeyboardMarkup | None = None
    photo: str | InputFile | None = None  # file_id, URL or local file; `text` becomes the caption

    @property
    def is_media(self) -> bool:
        return self.photo is not None


async def _send(message: Message, screen: Screen) -> Message:
    if screen.is_media:
        assert screen.photo is not None
        return await message.answer_photo(
            screen.photo, caption=screen.text, reply_markup=screen.markup
        )
    return await message.answer(screen.text, reply_markup=screen.markup)


async def send(message: Message, screen: Screen) -> Message:
    """Post a fresh screen (command entrypoints, after text input)."""
    return await _send(message, screen)


async def edit(query: CallbackQuery, screen: Screen) -> Message | None:
    """Update the message behind a callback in place, crossing media boundaries."""
    message = query.message
    if not isinstance(message, Message):
        # None, or an InaccessibleMessage (e.g. older than 48h) — nothing to edit.
        return None

    current_media = bool(message.photo)
    try:
        if screen.is_media and current_media:
            assert screen.photo is not None
            result = await message.edit_media(
                InputMediaPhoto(media=screen.photo, caption=screen.text),
                reply_markup=screen.markup,
            )
            return result if isinstance(result, Message) else None
        elif screen.is_media != current_media:
            # Crossing the text<->media boundary: replace the message.
            with suppress(TelegramBadRequest):
                await message.delete()
            return await _send(message, screen)
        else:
            result = await message.edit_text(screen.text, reply_markup=screen.markup)
            return result if isinstance(result, Message) else None
    except TelegramBadRequest as exc:
        if "not modified" in str(exc).lower():
            return None
        with suppress(TelegramBadRequest):
            await message.delete()
        return await _send(message, screen)
