"""Cart and checkout keyboards."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from playnext.application.dto import CheckoutPreview
from playnext.domain.models import Cart
from playnext.presentation.callbacks import CartCB, CheckoutCB, Nav, Noop
from playnext.presentation.keyboards.common import back_button


def cart_kb(cart: Cart) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for line in cart.lines:
        pid = line.product.id
        kb.row(
            InlineKeyboardButton(
                text=f"{line.product.title} · {line.subtotal.format()}",
                callback_data=Noop().pack(),
            )
        )
        kb.row(
            InlineKeyboardButton(
                text="-", callback_data=CartCB(action="dec", product_id=pid).pack()
            ),
            InlineKeyboardButton(text=f"{line.quantity} шт.", callback_data=Noop().pack()),
            InlineKeyboardButton(
                text="+", callback_data=CartCB(action="inc", product_id=pid).pack()
            ),
            InlineKeyboardButton(
                text="Удалить", callback_data=CartCB(action="del", product_id=pid).pack()
            ),
        )
    kb.row(
        InlineKeyboardButton(text="Очистить", callback_data=CartCB(action="clear").pack()),
        InlineKeyboardButton(text="Оформить", callback_data=CartCB(action="checkout").pack()),
    )
    kb.row(back_button("home"))
    return kb.as_markup()


def checkout_kb(preview: CheckoutPreview) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if preview.can_afford:
        kb.button(
            text=f"Оплатить {preview.total.format()}",
            callback_data=CheckoutCB(action="confirm"),
        )
    else:
        kb.button(text="Пополнить баланс", callback_data=Nav(to="wallet"))
    if preview.promo_code:
        kb.button(text="Убрать промокод", callback_data=CheckoutCB(action="clearpromo"))
    else:
        kb.button(text="Ввести промокод", callback_data=CheckoutCB(action="promo"))
    kb.button(text="В корзину", callback_data=Nav(to="cart"))
    kb.adjust(1)
    return kb.as_markup()


def order_success_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="Мои покупки", callback_data=Nav(to="orders"))
    kb.button(text="В каталог", callback_data=Nav(to="catalog"))
    kb.adjust(1)
    return kb.as_markup()
