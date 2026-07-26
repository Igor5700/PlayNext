"""Shared keyboard primitives: main menu, back button, pagination."""

from __future__ import annotations

from collections.abc import Callable

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from playnext.presentation.callbacks import AdminCB, Nav, Noop


def main_menu(*, is_admin: bool = False) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="Каталог", callback_data=Nav(to="catalog"))
    kb.button(text="Избранное", callback_data=Nav(to="favorites"))
    kb.button(text="Корзина", callback_data=Nav(to="cart"))
    kb.button(text="Мои покупки", callback_data=Nav(to="orders"))
    kb.button(text="Кабинет", callback_data=Nav(to="profile"))
    kb.button(text="Поддержка", callback_data=Nav(to="support"))
    kb.adjust(2, 2, 2)
    if is_admin:
        kb.row(
            InlineKeyboardButton(
                text="Панель администратора", callback_data=AdminCB(to="home").pack()
            )
        )
    return kb.as_markup()


def back_button(to: str, *, label: str = "В меню") -> InlineKeyboardButton:
    return InlineKeyboardButton(text=label, callback_data=Nav(to=to).pack())


def home_row(kb: InlineKeyboardBuilder, *, label: str = "В меню") -> None:
    kb.row(back_button("home", label=label))


def add_pagination(
    kb: InlineKeyboardBuilder,
    *,
    page: int,
    pages: int,
    make_cb: Callable[[int], CallbackData],
) -> None:
    if pages <= 1:
        return
    row: list[InlineKeyboardButton] = []
    if page > 1:
        row.append(InlineKeyboardButton(text="<", callback_data=make_cb(page - 1).pack()))
    row.append(InlineKeyboardButton(text=f"{page}/{pages}", callback_data=Noop().pack()))
    if page < pages:
        row.append(InlineKeyboardButton(text=">", callback_data=make_cb(page + 1).pack()))
    kb.row(*row)
