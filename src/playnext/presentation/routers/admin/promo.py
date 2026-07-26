"""Admin: promo code management."""

from __future__ import annotations

import re

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from playnext.application.services import Services
from playnext.core.money import Money, parse_major
from playnext.domain.enums import DiscountType
from playnext.domain.models import PromoCode
from playnext.presentation import screen, texts
from playnext.presentation.callbacks import AdminPromoCB
from playnext.presentation.fsm_data import PromoDraftData, get_typed
from playnext.presentation.keyboards.admin import admin_promos_kb
from playnext.presentation.screen import Screen
from playnext.presentation.states import AdminPromoFlow

router = Router(name="admin_promo")

_CODE_RE = re.compile(r"^[A-Z0-9]{3,32}$")


async def _list_screen(services: Services) -> Screen:
    promos = await services.admin.promos()
    if not promos:
        return Screen(text=texts.ADMIN_PROMOS_EMPTY, markup=admin_promos_kb(promos))
    return Screen(text="<b>Промокоды</b>", markup=admin_promos_kb(promos))


@router.callback_query(AdminPromoCB.filter(F.action == "list"))
async def list_promos(cb: CallbackQuery, services: Services, state: FSMContext) -> None:
    await state.clear()
    await screen.edit(cb, await _list_screen(services))
    await cb.answer()


@router.callback_query(AdminPromoCB.filter(F.action == "add"))
async def add_promo(cb: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminPromoFlow.code)
    await screen.edit(cb, Screen(text=texts.ADMIN_PROMO_CODE_PROMPT))
    await cb.answer()


@router.message(AdminPromoFlow.code, F.text)
async def promo_code(message: Message, state: FSMContext) -> None:
    code = (message.text or "").strip().upper()
    if not _CODE_RE.match(code):
        await message.answer("Код: 3–32 символа, латиница и цифры. Попробуйте снова.")
        return
    await state.update_data(code=code)
    await state.set_state(AdminPromoFlow.discount)
    await message.answer(texts.ADMIN_PROMO_DISCOUNT_PROMPT)


@router.message(AdminPromoFlow.discount, F.text)
async def promo_discount(message: Message, services: Services, state: FSMContext) -> None:
    raw = (message.text or "").strip().replace(" ", "")
    data = await get_typed(state, PromoDraftData)
    if raw.endswith("%"):
        try:
            percent = int(raw[:-1])
        except ValueError:
            await message.answer("Введите процент, например 10%.")
            return
        if not 1 <= percent <= 100:
            await message.answer("Процент должен быть от 1 до 100.")
            return
        discount_type, value = DiscountType.PERCENT, percent
    else:
        parsed = parse_major(raw)
        if parsed is None:
            await message.answer("Введите число (300) или процент (10%).")
            return
        amount = Money.from_major(parsed)
        if not amount.is_positive:
            await message.answer("Сумма должна быть больше нуля.")
            return
        discount_type, value = DiscountType.FIXED, amount.minor

    await services.admin.create_promo(
        PromoCode(code=data["code"], discount_type=discount_type, value=value)
    )
    await state.clear()
    await screen.send(message, await _list_screen(services))


@router.callback_query(AdminPromoCB.filter(F.action == "toggle"))
async def toggle_promo(cb: CallbackQuery, callback_data: AdminPromoCB, services: Services) -> None:
    promos = await services.admin.promos()
    current = next((p for p in promos if p.code == callback_data.code), None)
    if current is not None:
        await services.admin.toggle_promo(current.code, not current.is_active)
    await screen.edit(cb, await _list_screen(services))
    await cb.answer("Готово")
