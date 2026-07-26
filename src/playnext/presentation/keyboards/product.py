"""Product card keyboard."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from playnext.domain.models import Product
from playnext.presentation.callbacks import CatalogCB, ProductCB


def product_kb(
    product: Product,
    *,
    category_id: int,
    page: int,
    in_cart: int,
    is_favorite: bool,
    similar: list[Product],
) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()

    def cb(action: str) -> str:
        return ProductCB(
            action=action, product_id=product.id, category_id=category_id, page=page
        ).pack()

    if product.in_stock:
        kb.row(InlineKeyboardButton(text="Купить сейчас", callback_data=cb("buy_now")))
        add_label = "В корзину" if in_cart == 0 else f"Ещё одну ({in_cart} в корзине)"
        kb.row(InlineKeyboardButton(text=add_label, callback_data=cb("add")))

    fav_label = "Убрать из избранного" if is_favorite else "В избранное"
    kb.row(
        InlineKeyboardButton(text=fav_label, callback_data=cb("favorite")),
        InlineKeyboardButton(text="Поделиться", callback_data=cb("share")),
    )

    for item in similar:
        kb.row(
            InlineKeyboardButton(
                text=f"{item.title} · {item.price.format()}",
                callback_data=ProductCB(
                    action="open", product_id=item.id, category_id=item.category_id, page=1
                ).pack(),
            )
        )

    kb.row(
        InlineKeyboardButton(
            text="Назад", callback_data=CatalogCB(category_id=category_id, page=page).pack()
        )
    )
    return kb.as_markup()
