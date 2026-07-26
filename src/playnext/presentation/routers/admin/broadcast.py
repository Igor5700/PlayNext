"""Admin: broadcast a message to every user."""

from __future__ import annotations

import asyncio
import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from playnext.application.services import Services
from playnext.presentation import screen, texts
from playnext.presentation.callbacks import AdminCB
from playnext.presentation.keyboards.admin import admin_back_home_kb
from playnext.presentation.screen import Screen
from playnext.presentation.states import AdminBroadcastFlow

router = Router(name="admin_broadcast")
logger = logging.getLogger("playnext.broadcast")


@router.callback_query(AdminCB.filter(F.to == "broadcast"))
async def ask_broadcast(cb: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminBroadcastFlow.message)
    await screen.edit(cb, Screen(text=texts.ADMIN_BROADCAST_PROMPT, markup=admin_back_home_kb()))
    await cb.answer()


@router.message(AdminBroadcastFlow.message)
async def do_broadcast(message: Message, services: Services, state: FSMContext) -> None:
    await state.clear()
    recipients = await services.admin.broadcast_recipients()
    sent = 0
    failed = 0
    status = await message.answer(f"Рассылка запущена: 0/{len(recipients)}")

    for index, user_id in enumerate(recipients, 1):
        try:
            await message.send_copy(chat_id=user_id)
            sent += 1
        except TelegramRetryAfter as exc:
            await asyncio.sleep(exc.retry_after)
            try:
                await message.send_copy(chat_id=user_id)
                sent += 1
            except Exception:
                failed += 1
        except TelegramForbiddenError:
            failed += 1  # user blocked the bot
        except Exception:
            failed += 1
            logger.warning("Broadcast to %s failed", user_id)

        if index % 25 == 0:
            await status.edit_text(f"Рассылка: {index}/{len(recipients)}")
        await asyncio.sleep(0.05)  # ~20 msg/s, safely under Telegram limits

    await status.edit_text(
        f"Рассылка завершена.\nДоставлено: {sent}\nНе доставлено: {failed}",
        reply_markup=admin_back_home_kb(),
    )
