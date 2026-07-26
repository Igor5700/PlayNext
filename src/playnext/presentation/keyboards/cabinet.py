"""Cabinet (personal account) and purchase-history keyboards."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from playnext.application.dto import Page
from playnext.domain.models import Order
from playnext.presentation.callbacks import CatalogFilterCB, Nav, OrdersCB
from playnext.presentation.formatting import order_row
from playnext.presentation.keyboards.common import add_pagination, back_button


def cabinet_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="Баланс", callback_data=Nav(to="wallet"))
    kb.button(text="Мои покупки", callback_data=Nav(to="orders"))
    kb.button(text="Скидки", callback_data=CatalogFilterCB(kind="discounts"))
    kb.adjust(2, 1)
    kb.row(back_button("home"))
    return kb.as_markup()


def orders_kb(page: Page[Order]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for order in page.items:
        kb.button(
            text=order_row(order),
            callback_data=OrdersCB(action="open", order_id=order.id, page=page.page),
        )
    kb.adjust(1)
    add_pagination(
        kb, page=page.page, pages=page.pages, make_cb=lambda p: OrdersCB(action="list", page=p)
    )
    kb.row(back_button("home"))
    return kb.as_markup()


def order_detail_kb(page: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(
            text="К покупкам", callback_data=OrdersCB(action="list", page=page).pack()
        )
    )
    return kb.as_markup()
