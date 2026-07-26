"""Catch-all for unmatched input — always lands the user back on the menu."""

from __future__ import annotations

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from playnext.core.config import Settings
from playnext.domain.models import User
from playnext.presentation import screen
from playnext.presentation.home_screen import cache_banner, home_screen

router = Router(name="fallback")


@router.message()
async def fallback(message: Message, user: User, settings: Settings, state: FSMContext) -> None:
    await state.clear()
    if message.text and message.text.startswith("/"):
        return
    sent = await screen.send(message, home_screen(user, settings))
    cache_banner(sent)
