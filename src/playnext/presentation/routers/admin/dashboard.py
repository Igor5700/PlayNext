"""Admin dashboard: entry command and stats overview."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from playnext.application.services import Services
from playnext.presentation import screen, texts
from playnext.presentation.callbacks import AdminCB
from playnext.presentation.formatting import admin_stats_text
from playnext.presentation.keyboards.admin import admin_home_kb
from playnext.presentation.screen import Screen

router = Router(name="admin_dashboard")


async def _home_screen(services: Services) -> Screen:
    stats = await services.admin.stats()
    return Screen(text=f"{texts.ADMIN_HOME}\n\n{admin_stats_text(stats)}", markup=admin_home_kb())


@router.message(Command("admin"))
async def cmd_admin(message: Message, services: Services, state: FSMContext) -> None:
    await state.clear()
    await screen.send(message, await _home_screen(services))


@router.callback_query(AdminCB.filter(F.to == "home"))
async def admin_home(cb: CallbackQuery, services: Services, state: FSMContext) -> None:
    await state.clear()
    await screen.edit(cb, await _home_screen(services))
    await cb.answer()
