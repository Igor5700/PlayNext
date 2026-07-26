"""Admin: user list and block/unblock."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from playnext.application.services import Services
from playnext.presentation import screen
from playnext.presentation.callbacks import AdminUserCB
from playnext.presentation.keyboards.admin import admin_users_kb
from playnext.presentation.screen import Screen

router = Router(name="admin_users")


async def _list_screen(services: Services, page: int) -> Screen:
    page_obj = await services.admin.users(page=page)
    text = (
        f"<b>Пользователи</b> ({page_obj.total})\nНажмите, чтобы заблокировать или разблокировать."
    )
    return Screen(text=text, markup=admin_users_kb(page_obj))


@router.callback_query(AdminUserCB.filter(F.action == "list"))
async def list_users(
    cb: CallbackQuery, callback_data: AdminUserCB, services: Services, state: FSMContext
) -> None:
    await state.clear()
    await screen.edit(cb, await _list_screen(services, callback_data.page))
    await cb.answer()


@router.callback_query(AdminUserCB.filter(F.action == "block"))
async def block_user(cb: CallbackQuery, callback_data: AdminUserCB, services: Services) -> None:
    await services.admin.set_user_blocked(callback_data.user_id, True)
    await screen.edit(cb, await _list_screen(services, callback_data.page))
    await cb.answer("Заблокирован")


@router.callback_query(AdminUserCB.filter(F.action == "unblock"))
async def unblock_user(cb: CallbackQuery, callback_data: AdminUserCB, services: Services) -> None:
    await services.admin.set_user_blocked(callback_data.user_id, False)
    await screen.edit(cb, await _list_screen(services, callback_data.page))
    await cb.answer("Разблокирован")
