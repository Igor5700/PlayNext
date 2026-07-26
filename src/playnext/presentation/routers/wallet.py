"""Wallet: balance, top-up via payment gateway, transaction history."""

from __future__ import annotations

import asyncio

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from playnext.application.services import Services
from playnext.application.services.payment_service import MAX_TOPUP, MIN_TOPUP
from playnext.core.money import Money, parse_major
from playnext.domain.enums import PaymentStatus
from playnext.domain.models import User
from playnext.presentation import screen, texts
from playnext.presentation.callbacks import Nav, PayCB, WalletCB
from playnext.presentation.formatting import transaction_row, wallet_text
from playnext.presentation.keyboards.common import back_button
from playnext.presentation.keyboards.wallet import (
    history_kb,
    payment_kb,
    provider_choice_kb,
    topup_kb,
    wallet_kb,
)
from playnext.presentation.screen import Screen
from playnext.presentation.states import WalletFlow

router = Router(name="wallet")

_DEMO_PROCESSING_DELAY = 1.5


def _back_only() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[back_button("home")]])


async def _wallet_screen(services: Services, user: User, *, note: str = "") -> Screen:
    balance = await services.wallet.balance(user.id)
    text = wallet_text(balance, providers=tuple(services.payment.available_providers()))
    if note:
        text = f"{note}\n\n{text}"
    return Screen(text=text, markup=wallet_kb())


def _provider_choice_screen(services: Services, amount: Money) -> Screen:
    providers = services.payment.available_providers()
    return Screen(
        text=f"Как пополнить?\n\nСумма: <b>{amount.format()}</b>",
        markup=provider_choice_kb(int(amount.major), providers=providers),
    )


async def _create_real_topup(services: Services, user: User, amount: Money) -> Screen:
    ticket = await services.payment.create_topup(user.id, amount, provider="crypto_pay")
    return Screen(
        text=f"{texts.WALLET_TOPUP_CREATED}\n\nСумма: <b>{amount.format()}</b>",
        markup=payment_kb(ticket.payment_id, ticket.confirmation_url),
    )


async def _demo_topup_result(services: Services, user: User, amount: Money) -> Screen:
    """Create + instantly settle a demo top-up (no external gateway round-trip)."""
    ticket = await services.payment.create_topup(user.id, amount, provider="demo")
    status = await services.payment.check_topup(user.id, ticket.payment_id)
    if status is not PaymentStatus.SUCCEEDED:
        return Screen(text=texts.GENERIC_ERROR, markup=_back_only())
    note = f"{texts.WALLET_TOPUP_SUCCESS}\n\n+{amount.format()} · Demo payment · Успешно"
    return await _wallet_screen(services, user, note=note)


def _processing_screen(amount: Money) -> Screen:
    return Screen(text=f"{texts.WALLET_TOPUP_PROCESSING}\n\nСумма: <b>{amount.format()}</b>")


@router.callback_query(Nav.filter(F.to == "wallet"))
async def show_wallet(cb: CallbackQuery, services: Services, user: User, state: FSMContext) -> None:
    await state.clear()
    await screen.edit(cb, await _wallet_screen(services, user))
    await cb.answer()


@router.callback_query(WalletCB.filter(F.action == "topup"))
async def topup_menu(cb: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await screen.edit(cb, Screen(text="Выберите сумму пополнения", markup=topup_kb()))
    await cb.answer()


@router.callback_query(WalletCB.filter(F.action == "preset"))
async def topup_preset(cb: CallbackQuery, callback_data: WalletCB, services: Services) -> None:
    amount = Money.from_major(callback_data.amount)
    await screen.edit(cb, _provider_choice_screen(services, amount))
    await cb.answer()


@router.callback_query(WalletCB.filter(F.action == "manual"))
async def topup_manual(cb: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(WalletFlow.amount)
    await screen.edit(cb, Screen(text=texts.WALLET_TOPUP_PROMPT, markup=_back_only()))
    await cb.answer()


@router.message(WalletFlow.amount, F.text)
async def topup_amount(message: Message, services: Services, state: FSMContext) -> None:
    value = parse_major(message.text or "")
    if value is None or value <= 0:
        await message.answer(texts.WALLET_TOPUP_INVALID)
        return
    amount = Money.from_major(value)
    if amount.minor < MIN_TOPUP.minor or amount.minor > MAX_TOPUP.minor:
        await message.answer(f"Сумма должна быть от {MIN_TOPUP.format()} до {MAX_TOPUP.format()}.")
        return
    await state.clear()
    await screen.send(message, _provider_choice_screen(services, amount))


@router.callback_query(WalletCB.filter(F.action == "provider"))
async def topup_provider(
    cb: CallbackQuery, callback_data: WalletCB, services: Services, user: User
) -> None:
    amount = Money.from_major(callback_data.amount)
    if callback_data.provider == "demo":
        await screen.edit(cb, _processing_screen(amount))
        await asyncio.sleep(_DEMO_PROCESSING_DELAY)
        await screen.edit(cb, await _demo_topup_result(services, user, amount))
    else:
        await screen.edit(cb, await _create_real_topup(services, user, amount))
    await cb.answer()


@router.callback_query(PayCB.filter(F.action == "check"))
async def check_payment(
    cb: CallbackQuery, callback_data: PayCB, services: Services, user: User
) -> None:
    status = await services.payment.check_topup(user.id, callback_data.payment_id)
    if status is PaymentStatus.SUCCEEDED:
        await screen.edit(cb, await _wallet_screen(services, user, note=texts.WALLET_TOPUP_SUCCESS))
        await cb.answer(texts.WALLET_TOPUP_SUCCESS)
    elif status is PaymentStatus.PENDING:
        await cb.answer(texts.WALLET_TOPUP_PENDING, show_alert=True)
    else:
        await screen.edit(
            cb, await _wallet_screen(services, user, note=texts.WALLET_TOPUP_CANCELLED)
        )
        await cb.answer()


@router.callback_query(PayCB.filter(F.action == "cancel"))
async def cancel_payment(
    cb: CallbackQuery, callback_data: PayCB, services: Services, user: User
) -> None:
    await services.payment.cancel_topup(user.id, callback_data.payment_id)
    await screen.edit(cb, await _wallet_screen(services, user, note=texts.WALLET_TOPUP_CANCELLED))
    await cb.answer()


@router.callback_query(WalletCB.filter(F.action == "history"))
async def history(
    cb: CallbackQuery, callback_data: WalletCB, services: Services, user: User
) -> None:
    page = await services.wallet.transactions(user.id, page=callback_data.page)
    if page.is_empty:
        await screen.edit(cb, Screen(text=texts.HISTORY_EMPTY, markup=wallet_kb()))
    else:
        body = "\n".join(transaction_row(txn) for txn in page.items)
        text = f"{texts.HISTORY_TITLE}\n\n{body}"
        await screen.edit(cb, Screen(text=text, markup=history_kb(page)))
    await cb.answer()
