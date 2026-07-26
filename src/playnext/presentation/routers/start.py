"""Entry points and top-level navigation (home, support, shared-product deep links)."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from playnext.application.services import Services
from playnext.core.config import Settings
from playnext.domain.errors import ProductNotFound
from playnext.domain.models import User
from playnext.presentation import screen, texts
from playnext.presentation.callbacks import Nav
from playnext.presentation.home_screen import cache_banner, home_screen
from playnext.presentation.keyboards.common import back_button
from playnext.presentation.routers.catalog import product_screen
from playnext.presentation.screen import Screen

router = Router(name="start")


def _back_only() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[back_button("home")]])


async def _open_shared_product(
    message: Message, services: Services, user: User, payload: str
) -> bool:
    """Returns True if the payload was a valid product link and was handled."""
    if not payload.startswith("product_"):
        return False
    try:
        product_id = int(payload.removeprefix("product_"))
    except ValueError:
        return False
    try:
        product = await services.catalog.product(product_id)
    except ProductNotFound:
        return False
    await services.catalog.record_view(user.id, product.id)
    scr = await product_screen(services, user, product, category_id=product.category_id, page=1)
    await screen.send(message, scr)
    return True


@router.message(CommandStart())
async def cmd_start(
    message: Message,
    user: User,
    settings: Settings,
    state: FSMContext,
    services: Services,
    command: CommandObject,
) -> None:
    await state.clear()
    if command.args and await _open_shared_product(message, services, user, command.args):
        return
    sent = await screen.send(message, home_screen(user, settings))
    cache_banner(sent)


@router.callback_query(Nav.filter(F.to == "home"))
async def nav_home(cb: CallbackQuery, user: User, settings: Settings, state: FSMContext) -> None:
    await state.clear()
    edited = await screen.edit(cb, home_screen(user, settings))
    cache_banner(edited)
    await cb.answer()


@router.callback_query(Nav.filter(F.to == "support"))
async def nav_support(cb: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await screen.edit(cb, Screen(text=texts.SUPPORT, markup=_back_only()))
    await cb.answer()
