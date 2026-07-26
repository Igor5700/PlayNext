"""Favorites (wishlist)."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup

from playnext.application.services import Services
from playnext.domain.models import User
from playnext.presentation import screen, texts
from playnext.presentation.callbacks import FavoriteCB, Nav
from playnext.presentation.keyboards.common import back_button
from playnext.presentation.keyboards.favorites import favorites_kb
from playnext.presentation.screen import Screen

router = Router(name="favorites")


def _back_only() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[back_button("home")]])


async def _show(cb: CallbackQuery, services: Services, user: User, *, page: int) -> None:
    page_obj = await services.favorites.list(user.id, page=page)
    if page_obj.is_empty:
        await screen.edit(cb, Screen(text=texts.FAVORITES_EMPTY, markup=_back_only()))
    else:
        await screen.edit(
            cb,
            Screen(
                text=f"{texts.FAVORITES_TITLE} ({page_obj.total})", markup=favorites_kb(page_obj)
            ),
        )
    await cb.answer()


@router.callback_query(Nav.filter(F.to == "favorites"))
async def favorites_entry(
    cb: CallbackQuery, services: Services, user: User, state: FSMContext
) -> None:
    await state.clear()
    await _show(cb, services, user, page=1)


@router.callback_query(FavoriteCB.filter(F.action == "list"))
async def favorites_list(
    cb: CallbackQuery, callback_data: FavoriteCB, services: Services, user: User
) -> None:
    await _show(cb, services, user, page=callback_data.page)
