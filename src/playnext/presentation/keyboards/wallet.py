"""Wallet, top-up and payment keyboards."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from playnext.application.dto import Page
from playnext.domain.models import WalletTransaction
from playnext.presentation.callbacks import Nav, PayCB, WalletCB
from playnext.presentation.keyboards.common import add_pagination, back_button

_PRESETS = (300, 500, 1000, 2000, 3000, 5000)


def wallet_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="Пополнить", callback_data=WalletCB(action="topup"))
    kb.button(text="История", callback_data=WalletCB(action="history"))
    kb.adjust(2)
    kb.row(back_button("profile", label="В кабинет"))
    return kb.as_markup()


def topup_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for amount in _PRESETS:
        kb.button(text=f"{amount} ₽", callback_data=WalletCB(action="preset", amount=amount))
    kb.button(text="Другая сумма", callback_data=WalletCB(action="manual"))
    kb.adjust(3, 3, 1)
    kb.row(InlineKeyboardButton(text="Назад", callback_data=Nav(to="wallet").pack()))
    return kb.as_markup()


_PROVIDER_LABEL = {
    "demo": "Демо — бесплатно, мгновенно",
    "crypto_pay": "Crypto Pay — реальные деньги",
}


def provider_choice_kb(amount: int, *, providers: list[str]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for provider in providers:
        kb.row(
            InlineKeyboardButton(
                text=_PROVIDER_LABEL.get(provider, provider),
                callback_data=WalletCB(action="provider", amount=amount, provider=provider).pack(),
            )
        )
    kb.row(InlineKeyboardButton(text="Назад", callback_data=Nav(to="wallet").pack()))
    return kb.as_markup()


def payment_kb(payment_id: int, url: str | None) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if url:
        kb.button(text="Оплатить", url=url)
    kb.button(text="Проверить оплату", callback_data=PayCB(action="check", payment_id=payment_id))
    kb.button(text="Отменить", callback_data=PayCB(action="cancel", payment_id=payment_id))
    kb.adjust(1)
    return kb.as_markup()


def history_kb(page: Page[WalletTransaction]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    add_pagination(
        kb,
        page=page.page,
        pages=page.pages,
        make_cb=lambda p: WalletCB(action="history", page=p),
    )
    kb.row(InlineKeyboardButton(text="Баланс", callback_data=Nav(to="wallet").pack()))
    return kb.as_markup()
