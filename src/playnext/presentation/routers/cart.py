"""Cart management and checkout (with promo codes)."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from playnext.application.services import Services
from playnext.domain.errors import PromoInvalid
from playnext.domain.models import User
from playnext.presentation import screen, texts
from playnext.presentation.callbacks import CartCB, CheckoutCB, Nav
from playnext.presentation.formatting import cart_text, checkout_text, order_text
from playnext.presentation.fsm_data import CheckoutDraftData, get_typed
from playnext.presentation.keyboards.cart import cart_kb, checkout_kb, order_success_kb
from playnext.presentation.keyboards.common import back_button
from playnext.presentation.screen import Screen
from playnext.presentation.states import CheckoutFlow

router = Router(name="cart")


def _back_only() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[back_button("home")]])


async def _cart_screen(services: Services, user: User) -> Screen:
    cart = await services.cart.view(user.id)
    if cart.is_empty:
        return Screen(text=texts.CART_EMPTY, markup=_back_only())
    return Screen(text=cart_text(cart), markup=cart_kb(cart))


async def _checkout_screen(services: Services, user: User, promo: str | None) -> Screen:
    preview = await services.checkout.preview(user.id, promo_code=promo)
    return Screen(text=checkout_text(preview), markup=checkout_kb(preview))


# ── Cart ─────────────────────────────────────────────────────────────────────
@router.callback_query(Nav.filter(F.to == "cart"))
async def show_cart(cb: CallbackQuery, services: Services, user: User, state: FSMContext) -> None:
    await state.clear()
    await screen.edit(cb, await _cart_screen(services, user))
    await cb.answer()


@router.callback_query(CartCB.filter(F.action == "inc"))
async def inc(cb: CallbackQuery, callback_data: CartCB, services: Services, user: User) -> None:
    await services.cart.add(user.id, callback_data.product_id)
    await screen.edit(cb, await _cart_screen(services, user))
    await cb.answer()


@router.callback_query(CartCB.filter(F.action == "dec"))
async def dec(cb: CallbackQuery, callback_data: CartCB, services: Services, user: User) -> None:
    cart = await services.cart.view(user.id)
    current = next(
        (line.quantity for line in cart.lines if line.product.id == callback_data.product_id), 0
    )
    await services.cart.set_quantity(user.id, callback_data.product_id, current - 1)
    await screen.edit(cb, await _cart_screen(services, user))
    await cb.answer()


@router.callback_query(CartCB.filter(F.action == "del"))
async def remove(cb: CallbackQuery, callback_data: CartCB, services: Services, user: User) -> None:
    await services.cart.remove(user.id, callback_data.product_id)
    await screen.edit(cb, await _cart_screen(services, user))
    await cb.answer("Товар удалён")


@router.callback_query(CartCB.filter(F.action == "clear"))
async def clear(cb: CallbackQuery, services: Services, user: User) -> None:
    await services.cart.clear(user.id)
    await screen.edit(cb, await _cart_screen(services, user))
    await cb.answer("Корзина очищена")


# ── Checkout ─────────────────────────────────────────────────────────────────
@router.callback_query(CartCB.filter(F.action == "checkout"))
async def checkout(cb: CallbackQuery, services: Services, user: User, state: FSMContext) -> None:
    cart = await services.cart.view(user.id)
    if cart.is_empty:
        await screen.edit(cb, await _cart_screen(services, user))
        await cb.answer(texts.CART_EMPTY, show_alert=True)
        return
    await state.clear()
    await screen.edit(cb, await _checkout_screen(services, user, promo=None))
    await cb.answer()


@router.callback_query(CheckoutCB.filter(F.action == "promo"))
async def ask_promo(cb: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(CheckoutFlow.promo)
    await screen.edit(cb, Screen(text=texts.CHECKOUT_PROMO_PROMPT, markup=_back_only()))
    await cb.answer()


@router.message(CheckoutFlow.promo, F.text)
async def apply_promo(message: Message, services: Services, user: User, state: FSMContext) -> None:
    code = (message.text or "").strip().upper()
    try:
        await services.checkout.preview(user.id, promo_code=code)
    except PromoInvalid as exc:
        await message.answer(exc.user_message)
        return
    await state.update_data(promo=code)
    await state.set_state(None)
    await screen.send(message, await _checkout_screen(services, user, promo=code))


@router.callback_query(CheckoutCB.filter(F.action == "clearpromo"))
async def clear_promo(cb: CallbackQuery, services: Services, user: User, state: FSMContext) -> None:
    await state.update_data(promo=None)
    await screen.edit(cb, await _checkout_screen(services, user, promo=None))
    await cb.answer(texts.CHECKOUT_PROMO_REMOVED)


@router.callback_query(CheckoutCB.filter(F.action == "back"))
async def checkout_back(
    cb: CallbackQuery, services: Services, user: User, state: FSMContext
) -> None:
    await state.clear()
    await screen.edit(cb, await _cart_screen(services, user))
    await cb.answer()


@router.callback_query(CheckoutCB.filter(F.action == "confirm"))
async def confirm(cb: CallbackQuery, services: Services, user: User, state: FSMContext) -> None:
    data = await get_typed(state, CheckoutDraftData)
    promo = data.get("promo")
    order = await services.checkout.place_order(user.id, promo_code=promo)
    await state.clear()
    await screen.edit(
        cb,
        Screen(text=f"{texts.CHECKOUT_SUCCESS}\n\n{order_text(order)}", markup=order_success_kb()),
    )
    await cb.answer("Оплачено")
