"""Admin: payment browsing (read-only)."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from playnext.application.services import Services
from playnext.presentation import screen, texts
from playnext.presentation.callbacks import AdminPayCB
from playnext.presentation.keyboards.admin import admin_payments_kb
from playnext.presentation.screen import Screen

router = Router(name="admin_payments")


@router.callback_query(AdminPayCB.filter(F.action == "list"))
async def list_payments(
    cb: CallbackQuery, callback_data: AdminPayCB, services: Services, state: FSMContext
) -> None:
    await state.clear()
    page = await services.admin.payments(page=callback_data.page)
    if page.is_empty:
        await screen.edit(
            cb, Screen(text=texts.ADMIN_PAYMENTS_EMPTY, markup=admin_payments_kb(page))
        )
    else:
        await screen.edit(
            cb, Screen(text=f"<b>Платежи</b> ({page.total})", markup=admin_payments_kb(page))
        )
    await cb.answer()
