"""Admin: order browsing."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from playnext.application.services import Services
from playnext.presentation import screen, texts
from playnext.presentation.callbacks import AdminOrderCB
from playnext.presentation.formatting import order_text
from playnext.presentation.keyboards.admin import admin_order_kb, admin_orders_kb
from playnext.presentation.screen import Screen

router = Router(name="admin_orders")


@router.callback_query(AdminOrderCB.filter(F.action == "list"))
async def list_orders(
    cb: CallbackQuery, callback_data: AdminOrderCB, services: Services, state: FSMContext
) -> None:
    await state.clear()
    page = await services.admin.orders(page=callback_data.page)
    if page.is_empty:
        await screen.edit(cb, Screen(text=texts.ADMIN_ORDERS_EMPTY, markup=admin_orders_kb(page)))
    else:
        await screen.edit(
            cb, Screen(text=f"<b>Заказы</b> ({page.total})", markup=admin_orders_kb(page))
        )
    await cb.answer()


@router.callback_query(AdminOrderCB.filter(F.action == "open"))
async def open_order(cb: CallbackQuery, callback_data: AdminOrderCB, services: Services) -> None:
    order = await services.admin.order(callback_data.order_id)
    if order is None:
        await cb.answer(texts.PURCHASE_NOT_FOUND, show_alert=True)
        return
    text = f"Покупатель: <code>{order.user_id}</code>\n\n{order_text(order)}"
    await screen.edit(cb, Screen(text=text, markup=admin_order_kb(callback_data.page)))
    await cb.answer()
