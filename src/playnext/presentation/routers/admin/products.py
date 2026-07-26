"""Admin: product management, creation flow and key inventory."""

from __future__ import annotations

from html import escape

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State
from aiogram.types import CallbackQuery, Message

from playnext.application.services import Services
from playnext.core.money import Money, parse_major
from playnext.domain.models import Product
from playnext.presentation import screen, texts
from playnext.presentation.callbacks import AdminProdCB
from playnext.presentation.fsm_data import ProductDraftData, ProductEditTarget, get_typed
from playnext.presentation.keyboards.admin import admin_product_kb, admin_products_kb
from playnext.presentation.media import resolve_photo
from playnext.presentation.screen import Screen
from playnext.presentation.states import AdminProductFlow

router = Router(name="admin_products")


def _parse_price(raw: str) -> Money | None:
    value = parse_major(raw)
    return Money.from_major(value) if value is not None and value > 0 else None


def _detail_text(product: Product) -> str:
    status = "в продаже" if product.is_active else "снят с продажи"
    return (
        f"<b>{escape(product.title)}</b>\n"
        f"Цена: {product.price.format()}\n"
        f"Ключей в наличии: {product.stock}\n"
        f"Статус: {status}\n\n"
        f"{escape(product.description) if product.description else '—'}"
    )


async def _list_screen(services: Services, page: int) -> Screen:
    page_obj = await services.admin.products(page=page)
    if page_obj.is_empty:
        return Screen(text=texts.ADMIN_PRODUCTS_EMPTY, markup=admin_products_kb(page_obj))
    return Screen(text="<b>Товары</b>", markup=admin_products_kb(page_obj))


async def _detail_screen(services: Services, product_id: int, page: int) -> Screen:
    product = await services.admin.product(product_id)
    return Screen(
        text=_detail_text(product),
        markup=admin_product_kb(product, page=page),
        photo=resolve_photo(product.image_file_id),
    )


# ── Browse ───────────────────────────────────────────────────────────────────
@router.callback_query(AdminProdCB.filter(F.action == "list"))
async def list_products(
    cb: CallbackQuery, callback_data: AdminProdCB, services: Services, state: FSMContext
) -> None:
    await state.clear()
    await screen.edit(cb, await _list_screen(services, callback_data.page))
    await cb.answer()


@router.callback_query(AdminProdCB.filter(F.action == "open"))
async def open_product(
    cb: CallbackQuery, callback_data: AdminProdCB, services: Services, state: FSMContext
) -> None:
    await state.clear()
    await screen.edit(
        cb, await _detail_screen(services, callback_data.product_id, callback_data.page)
    )
    await cb.answer()


# ── Creation flow (product_id carries the category id here) ───────────────────
@router.callback_query(AdminProdCB.filter(F.action == "add"))
async def add_product(cb: CallbackQuery, callback_data: AdminProdCB, state: FSMContext) -> None:
    await state.set_state(AdminProductFlow.title)
    await state.update_data(category_id=callback_data.product_id)
    await screen.edit(cb, Screen(text=texts.ADMIN_PRODUCT_TITLE_PROMPT))
    await cb.answer()


@router.message(AdminProductFlow.title, F.text)
async def create_title(message: Message, state: FSMContext) -> None:
    title = (message.text or "").strip()
    if not title:
        await message.answer("Название не может быть пустым.")
        return
    await state.update_data(title=title)
    await state.set_state(AdminProductFlow.description)
    await message.answer(texts.ADMIN_PRODUCT_DESC_PROMPT)


@router.message(AdminProductFlow.description, F.text)
async def create_description(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    await state.update_data(description="" if text == "-" else text)
    await state.set_state(AdminProductFlow.price)
    await message.answer(texts.ADMIN_PRODUCT_PRICE_PROMPT)


@router.message(AdminProductFlow.price, F.text)
async def create_price(message: Message, state: FSMContext) -> None:
    price = _parse_price(message.text or "")
    if price is None:
        await message.answer("Введите положительное число, например 1500.")
        return
    await state.update_data(price_minor=price.minor)
    await state.set_state(AdminProductFlow.image)
    await message.answer(texts.ADMIN_PRODUCT_IMAGE_PROMPT)


async def _finish_create(
    message: Message, services: Services, state: FSMContext, image_file_id: str | None
) -> None:
    data = await get_typed(state, ProductDraftData)
    product = await services.admin.create_product(
        category_id=data["category_id"],
        title=data["title"],
        description=data["description"],
        price=Money(data["price_minor"]),
        image_file_id=image_file_id,
    )
    await state.clear()
    scr = await _detail_screen(services, product.id, page=1)
    note = "Товар создан. Добавьте ключи, чтобы он появился в продаже.\n\n"
    await screen.send(message, Screen(text=note + scr.text, markup=scr.markup, photo=scr.photo))


@router.message(AdminProductFlow.image, F.photo)
async def create_image_photo(message: Message, services: Services, state: FSMContext) -> None:
    assert message.photo is not None
    await _finish_create(message, services, state, message.photo[-1].file_id)


@router.message(AdminProductFlow.image, F.text)
async def create_image_skip(message: Message, services: Services, state: FSMContext) -> None:
    await _finish_create(message, services, state, None)


# ── Edits ────────────────────────────────────────────────────────────────────
@router.callback_query(AdminProdCB.filter(F.action == "title"))
async def edit_title(cb: CallbackQuery, callback_data: AdminProdCB, state: FSMContext) -> None:
    await _start_edit(
        cb, callback_data, state, AdminProductFlow.edit_title, texts.ADMIN_PRODUCT_TITLE_PROMPT
    )


@router.callback_query(AdminProdCB.filter(F.action == "price"))
async def edit_price(cb: CallbackQuery, callback_data: AdminProdCB, state: FSMContext) -> None:
    await _start_edit(
        cb, callback_data, state, AdminProductFlow.edit_price, texts.ADMIN_PRODUCT_PRICE_PROMPT
    )


@router.callback_query(AdminProdCB.filter(F.action == "desc"))
async def edit_desc(cb: CallbackQuery, callback_data: AdminProdCB, state: FSMContext) -> None:
    await _start_edit(
        cb, callback_data, state, AdminProductFlow.edit_description, texts.ADMIN_PRODUCT_DESC_PROMPT
    )


@router.callback_query(AdminProdCB.filter(F.action == "image"))
async def edit_image(cb: CallbackQuery, callback_data: AdminProdCB, state: FSMContext) -> None:
    await _start_edit(
        cb, callback_data, state, AdminProductFlow.edit_image, texts.ADMIN_PRODUCT_IMAGE_PROMPT
    )


async def _start_edit(
    cb: CallbackQuery,
    callback_data: AdminProdCB,
    state: FSMContext,
    target_state: State,
    prompt: str,
) -> None:
    await state.set_state(target_state)
    await state.update_data(product_id=callback_data.product_id, page=callback_data.page)
    await screen.edit(cb, Screen(text=prompt))
    await cb.answer()


async def _finish_edit(message: Message, services: Services, state: FSMContext) -> None:
    data = await get_typed(state, ProductEditTarget)
    await state.clear()
    await screen.send(message, await _detail_screen(services, data["product_id"], data["page"]))


@router.message(AdminProductFlow.edit_title, F.text)
async def do_edit_title(message: Message, services: Services, state: FSMContext) -> None:
    title = (message.text or "").strip()
    data = await get_typed(state, ProductEditTarget)
    if title:
        await services.admin.update_product(data["product_id"], title=title)
    await _finish_edit(message, services, state)


@router.message(AdminProductFlow.edit_price, F.text)
async def do_edit_price(message: Message, services: Services, state: FSMContext) -> None:
    price = _parse_price(message.text or "")
    data = await get_typed(state, ProductEditTarget)
    if price is None:
        await message.answer("Введите положительное число, например 1500.")
        return
    await services.admin.update_product(data["product_id"], price=price)
    await _finish_edit(message, services, state)


@router.message(AdminProductFlow.edit_description, F.text)
async def do_edit_desc(message: Message, services: Services, state: FSMContext) -> None:
    text = (message.text or "").strip()
    data = await get_typed(state, ProductEditTarget)
    await services.admin.update_product(data["product_id"], description="" if text == "-" else text)
    await _finish_edit(message, services, state)


@router.message(AdminProductFlow.edit_image, F.photo)
async def do_edit_image(message: Message, services: Services, state: FSMContext) -> None:
    assert message.photo is not None
    data = await get_typed(state, ProductEditTarget)
    await services.admin.update_product(data["product_id"], image_file_id=message.photo[-1].file_id)
    await _finish_edit(message, services, state)


@router.message(AdminProductFlow.edit_image, F.text)
async def do_edit_image_skip(message: Message, services: Services, state: FSMContext) -> None:
    await _finish_edit(message, services, state)


# ── Inventory: add keys ──────────────────────────────────────────────────────
@router.callback_query(AdminProdCB.filter(F.action == "keys"))
async def ask_keys(cb: CallbackQuery, callback_data: AdminProdCB, state: FSMContext) -> None:
    await state.set_state(AdminProductFlow.keys)
    await state.update_data(product_id=callback_data.product_id, page=callback_data.page)
    await screen.edit(cb, Screen(text=texts.ADMIN_KEYS_PROMPT))
    await cb.answer()


@router.message(AdminProductFlow.keys, F.text)
async def add_keys(message: Message, services: Services, state: FSMContext) -> None:
    secrets = [line.strip() for line in (message.text or "").splitlines() if line.strip()]
    data = await get_typed(state, ProductEditTarget)
    added = await services.admin.add_keys(data["product_id"], secrets)
    await state.clear()
    scr = await _detail_screen(services, data["product_id"], data["page"])
    await screen.send(
        message,
        Screen(text=f"Добавлено ключей: {added}\n\n{scr.text}", markup=scr.markup, photo=scr.photo),
    )


# ── Toggle / delete ──────────────────────────────────────────────────────────
@router.callback_query(AdminProdCB.filter(F.action == "toggle"))
async def toggle(cb: CallbackQuery, callback_data: AdminProdCB, services: Services) -> None:
    product = await services.admin.product(callback_data.product_id)
    await services.admin.toggle_product(product.id, not product.is_active)
    await screen.edit(cb, await _detail_screen(services, product.id, callback_data.page))
    await cb.answer("Готово")


@router.callback_query(AdminProdCB.filter(F.action == "del"))
async def delete(cb: CallbackQuery, callback_data: AdminProdCB, services: Services) -> None:
    await services.admin.delete_product(callback_data.product_id)
    await screen.edit(cb, await _list_screen(services, callback_data.page))
    await cb.answer("Товар удалён", show_alert=True)
