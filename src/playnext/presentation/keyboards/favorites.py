"""Favorites list keyboard."""

from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from playnext.application.dto import Page
from playnext.domain.models import Product
from playnext.presentation.callbacks import FavoriteCB, ProductCB
from playnext.presentation.keyboards.common import add_pagination, back_button


def favorites_kb(page: Page[Product]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for product in page.items:
        kb.button(
            text=f"{product.title} · {product.price.format()}",
            callback_data=ProductCB(
                action="open", product_id=product.id, category_id=product.category_id, page=1
            ),
        )
    kb.adjust(1)
    add_pagination(
        kb, page=page.page, pages=page.pages, make_cb=lambda p: FavoriteCB(action="list", page=p)
    )
    kb.row(back_button("home"))
    return kb.as_markup()
