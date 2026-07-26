"""Cabinet (personal account) and purchase history."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup

from playnext.application.services import Services
from playnext.domain.models import User
from playnext.presentation import screen, texts
from playnext.presentation.callbacks import Nav, OrdersCB
from playnext.presentation.formatting import cabinet_text, order_text
from playnext.presentation.keyboards.cabinet import cabinet_kb, order_detail_kb, orders_kb
from playnext.presentation.keyboards.common import back_button
from playnext.presentation.screen import Screen

router = Router(name="cabinet")


def _back_only() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[back_button("home")]])


@router.callback_query(Nav.filter(F.to == "profile"))
async def show_cabinet(cb: CallbackQuery, services: Services, state: FSMContext) -> None:
    await state.clear()
    assert cb.from_user is not None
    summary = await services.profile.summary(
        cb.from_user.id, username=cb.from_user.username, first_name=cb.from_user.first_name or ""
    )
    await screen.edit(cb, Screen(text=cabinet_text(summary), markup=cabinet_kb()))
    await cb.answer()


@router.callback_query(Nav.filter(F.to == "orders"))
async def orders_entry(
    cb: CallbackQuery, services: Services, user: User, state: FSMContext
) -> None:
    await state.clear()
    await _show_orders(cb, services, user, page=1)


@router.callback_query(OrdersCB.filter(F.action == "list"))
async def orders_list(
    cb: CallbackQuery, callback_data: OrdersCB, services: Services, user: User
) -> None:
    await _show_orders(cb, services, user, page=callback_data.page)


async def _show_orders(cb: CallbackQuery, services: Services, user: User, *, page: int) -> None:
    page_obj = await services.profile.orders(user.id, page=page)
    if page_obj.is_empty:
        await screen.edit(cb, Screen(text=texts.PURCHASES_EMPTY, markup=_back_only()))
    else:
        await screen.edit(
            cb,
            Screen(text=f"{texts.PURCHASES_TITLE} ({page_obj.total})", markup=orders_kb(page_obj)),
        )
    await cb.answer()


@router.callback_query(OrdersCB.filter(F.action == "open"))
async def open_order(
    cb: CallbackQuery, callback_data: OrdersCB, services: Services, user: User
) -> None:
    order = await services.profile.order(user.id, callback_data.order_id)
    await screen.edit(
        cb, Screen(text=order_text(order), markup=order_detail_kb(callback_data.page))
    )
    await cb.answer()
