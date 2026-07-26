"""Admin: category management."""

from __future__ import annotations

from html import escape

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from playnext.application.services import Services
from playnext.domain.models import Category
from playnext.presentation import screen, texts
from playnext.presentation.callbacks import AdminCatCB
from playnext.presentation.fsm_data import CategoryEditTarget, get_typed
from playnext.presentation.keyboards.admin import (
    admin_categories_kb,
    admin_category_kb,
)
from playnext.presentation.screen import Screen
from playnext.presentation.states import AdminCategoryFlow

router = Router(name="admin_categories")


def _detail_text(category: Category) -> str:
    status = "активна" if category.is_active else "скрыта"
    return f"<b>{escape(category.title)}</b>\nСтатус: {status}\nТоваров: {category.product_count}"


async def _list_screen(services: Services) -> Screen:
    categories = await services.admin.categories()
    return Screen(text="<b>Категории</b>", markup=admin_categories_kb(categories))


async def _detail_screen(services: Services, category_id: int) -> Screen:
    category = await services.admin.category(category_id)
    return Screen(text=_detail_text(category), markup=admin_category_kb(category))


@router.callback_query(AdminCatCB.filter(F.action == "open"))
async def open_categories(
    cb: CallbackQuery, callback_data: AdminCatCB, services: Services, state: FSMContext
) -> None:
    await state.clear()
    if callback_data.category_id:
        await screen.edit(cb, await _detail_screen(services, callback_data.category_id))
    else:
        await screen.edit(cb, await _list_screen(services))
    await cb.answer()


@router.callback_query(AdminCatCB.filter(F.action == "add"))
async def add_category(cb: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminCategoryFlow.title)
    await screen.edit(cb, Screen(text=texts.ADMIN_CATEGORY_TITLE_PROMPT))
    await cb.answer()


@router.message(AdminCategoryFlow.title, F.text)
async def create_category(message: Message, services: Services, state: FSMContext) -> None:
    title = (message.text or "").strip()
    if not title:
        await message.answer("Название не может быть пустым.")
        return
    category = await services.admin.create_category(title=title)
    await state.clear()
    await screen.send(message, await _detail_screen(services, category.id))


@router.callback_query(AdminCatCB.filter(F.action == "rename"))
async def ask_rename(cb: CallbackQuery, callback_data: AdminCatCB, state: FSMContext) -> None:
    await state.set_state(AdminCategoryFlow.rename)
    await state.update_data(category_id=callback_data.category_id)
    await screen.edit(cb, Screen(text=texts.ADMIN_CATEGORY_TITLE_PROMPT))
    await cb.answer()


@router.message(AdminCategoryFlow.rename, F.text)
async def do_rename(message: Message, services: Services, state: FSMContext) -> None:
    title = (message.text or "").strip()
    data = await get_typed(state, CategoryEditTarget)
    if title:
        await services.admin.rename_category(data["category_id"], title)
    await state.clear()
    await screen.send(message, await _detail_screen(services, data["category_id"]))


@router.callback_query(AdminCatCB.filter(F.action == "toggle"))
async def toggle(cb: CallbackQuery, callback_data: AdminCatCB, services: Services) -> None:
    category = await services.admin.category(callback_data.category_id)
    await services.admin.toggle_category(category.id, not category.is_active)
    await screen.edit(cb, await _detail_screen(services, category.id))
    await cb.answer("Готово")


@router.callback_query(AdminCatCB.filter(F.action == "del"))
async def delete(cb: CallbackQuery, callback_data: AdminCatCB, services: Services) -> None:
    await services.admin.delete_category(callback_data.category_id)
    await screen.edit(cb, await _list_screen(services))
    await cb.answer("Категория удалена", show_alert=True)
