"""Catalog: category grid, quick filters, product list, product card, search."""

from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from playnext.application.dto import Page
from playnext.application.services import Services
from playnext.domain.models import Category, Product, User
from playnext.presentation import screen, texts
from playnext.presentation.callbacks import (
    CatalogCB,
    CatalogFilterCB,
    FeaturedCB,
    GroupCB,
    Nav,
    ProductCB,
    SearchCB,
)
from playnext.presentation.formatting import (
    category_header,
    checkout_text,
    discount_row,
    product_caption,
)
from playnext.presentation.keyboards.cart import checkout_kb
from playnext.presentation.keyboards.catalog import (
    catalog_home_kb,
    featured_showcase_kb,
    product_shelf_kb,
    products_kb,
    search_results_kb,
    variant_group_kb,
)
from playnext.presentation.keyboards.common import back_button
from playnext.presentation.keyboards.product import product_kb
from playnext.presentation.media import resolve_photo
from playnext.presentation.screen import Screen
from playnext.presentation.states import SearchFlow

router = Router(name="catalog")


def _back_only() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[back_button("home")]])


def _shelf_screen(title: str, products: list[Product]) -> Screen:
    if not products:
        return Screen(text=texts.CATALOG_EMPTY, markup=_back_only())
    return Screen(text=title, markup=product_shelf_kb(products))


async def product_screen(
    services: Services, user: User, product: Product, *, category_id: int, page: int
) -> Screen:
    """Build the product-card screen. Shared with the /start deep-link entry point."""
    cart = await services.cart.view(user.id)
    in_cart = next((line.quantity for line in cart.lines if line.product.id == product.id), 0)
    is_favorite = await services.favorites.is_favorite(user.id, product.id)
    similar = await services.catalog.similar(product.id)
    sold_count = await services.catalog.sold_count(product.id)
    text = product_caption(product, in_cart=in_cart, sold_count=sold_count)
    if similar:
        text += f"\n\n{texts.SIMILAR_HEADING}"
    return Screen(
        text=text,
        markup=product_kb(
            product,
            category_id=category_id,
            page=page,
            in_cart=in_cart,
            is_favorite=is_favorite,
            similar=similar,
        ),
        photo=resolve_photo(product.image_file_id),
    )


# ── Catalog home & categories ───────────────────────────────────────────────
async def _featured_items(services: Services) -> list[Product]:
    """Featured games for the showcase, deduping variant editions (e.g. GTA 6)
    down to one representative entry each. Multi-edition titles are the
    marquee releases, so they lead the showcase."""
    raw = await services.catalog.featured(limit=10)
    grouped: list[Product] = []
    standalone: list[Product] = []
    seen_groups: set[str] = set()
    for product in raw:
        if product.variant_group:
            if product.variant_group in seen_groups:
                continue
            seen_groups.add(product.variant_group)
            grouped.append(product)
        else:
            standalone.append(product)
    return grouped + standalone


async def _catalog_home_screen(
    services: Services, user: User, categories: list[Category], *, index: int = 0
) -> Screen:
    has_recent = bool(await services.catalog.recently_viewed(user.id, limit=1))
    items = await _featured_items(services)
    if not items:
        return Screen(
            text=f"{texts.CATALOG_TITLE}\n\n{texts.CATALOG_HINT}",
            markup=catalog_home_kb(categories, has_recent=has_recent),
        )
    index %= len(items)
    current = items[index]
    sold_count = await services.catalog.sold_count(current.id)
    text = f"{texts.CATALOG_TOP_HEADING}\n\n{product_caption(current, sold_count=sold_count)}"
    markup = featured_showcase_kb(
        items, index=index, current=current, categories=categories, has_recent=has_recent
    )
    return Screen(text=text, markup=markup, photo=resolve_photo(current.image_file_id))


@router.callback_query(Nav.filter(F.to == "catalog"))
async def show_categories(
    cb: CallbackQuery, services: Services, user: User, state: FSMContext
) -> None:
    await state.clear()
    categories = await services.catalog.categories()
    if not categories:
        await screen.edit(cb, Screen(text=texts.CATALOG_EMPTY, markup=_back_only()))
        await cb.answer()
        return
    await screen.edit(cb, await _catalog_home_screen(services, user, categories))
    await cb.answer()


@router.callback_query(FeaturedCB.filter())
async def show_featured(
    cb: CallbackQuery, callback_data: FeaturedCB, services: Services, user: User
) -> None:
    categories = await services.catalog.categories()
    if categories:
        await screen.edit(
            cb, await _catalog_home_screen(services, user, categories, index=callback_data.index)
        )
    await cb.answer()


@router.callback_query(CatalogFilterCB.filter())
async def catalog_filter(
    cb: CallbackQuery, callback_data: CatalogFilterCB, services: Services, user: User
) -> None:
    kind = callback_data.kind
    if kind == "newest":
        await screen.edit(cb, _shelf_screen(texts.NEWEST_TITLE, await services.catalog.newest()))
    elif kind == "popular":
        await screen.edit(cb, _shelf_screen(texts.POPULAR_TITLE, await services.catalog.popular()))
    elif kind == "recent":
        recent = await services.catalog.recently_viewed(user.id)
        await screen.edit(cb, _shelf_screen(texts.RECENT_TITLE, recent))
    elif kind == "discounts":
        promos = await services.catalog.active_promos()
        if not promos:
            await screen.edit(cb, Screen(text=texts.DISCOUNTS_EMPTY, markup=_back_only()))
        else:
            body = "\n".join(discount_row(p) for p in promos)
            text = f"{texts.DISCOUNTS_TITLE}\n\n{body}\n\n{texts.DISCOUNTS_HINT}"
            await screen.edit(cb, Screen(text=text, markup=_back_only()))
    await cb.answer()


@router.callback_query(GroupCB.filter())
async def show_group(
    cb: CallbackQuery, callback_data: GroupCB, services: Services, state: FSMContext
) -> None:
    await state.clear()
    members = await services.catalog.variant_group(callback_data.group)
    if not members:
        await cb.answer(texts.NOT_FOUND_ALERT, show_alert=True)
        return
    first = members[0]
    header = first.title.split(" (")[0]
    text = (
        f"<b>{header}</b>\n\n"
        "Платформа: PS5\n"
        "Перевод: русские субтитры\n\n"
        f"<i>{texts.GTA6_STORY}</i>\n\n"
        "Выберите издание:"
    )
    await screen.edit(
        cb,
        Screen(
            text=text, markup=variant_group_kb(members), photo=resolve_photo(first.image_file_id)
        ),
    )
    await cb.answer()


@router.callback_query(CatalogCB.filter())
async def show_products(
    cb: CallbackQuery, callback_data: CatalogCB, services: Services, state: FSMContext
) -> None:
    await state.clear()
    category = await services.catalog.category(callback_data.category_id)
    page = await services.catalog.products(callback_data.category_id, page=callback_data.page)
    if page.is_empty:
        await screen.edit(cb, Screen(text=texts.CATEGORY_EMPTY, markup=_back_only()))
    else:
        await screen.edit(
            cb,
            Screen(
                text=category_header(category, page=page.page, pages=page.pages),
                markup=products_kb(page, category_id=category.id),
            ),
        )
    await cb.answer()


# ── Product card ─────────────────────────────────────────────────────────────
@router.callback_query(ProductCB.filter(F.action == "open"))
async def open_product(
    cb: CallbackQuery, callback_data: ProductCB, services: Services, user: User, state: FSMContext
) -> None:
    await state.clear()
    product = await services.catalog.product(callback_data.product_id)
    await services.catalog.record_view(user.id, product.id)
    await screen.edit(
        cb,
        await product_screen(
            services, user, product, category_id=callback_data.category_id, page=callback_data.page
        ),
    )
    await cb.answer()


@router.callback_query(ProductCB.filter(F.action == "add"))
async def add_to_cart(
    cb: CallbackQuery, callback_data: ProductCB, services: Services, user: User
) -> None:
    await services.cart.add(user.id, callback_data.product_id)
    product = await services.catalog.product(callback_data.product_id)
    await screen.edit(
        cb,
        await product_screen(
            services, user, product, category_id=callback_data.category_id, page=callback_data.page
        ),
    )
    await cb.answer("Добавлено в корзину")


@router.callback_query(ProductCB.filter(F.action == "buy_now"))
async def buy_now(
    cb: CallbackQuery, callback_data: ProductCB, services: Services, user: User, state: FSMContext
) -> None:
    await services.cart.add(user.id, callback_data.product_id)
    await state.clear()
    preview = await services.checkout.preview(user.id)
    await screen.edit(cb, Screen(text=checkout_text(preview), markup=checkout_kb(preview)))
    await cb.answer()


@router.callback_query(ProductCB.filter(F.action == "favorite"))
async def toggle_favorite(
    cb: CallbackQuery, callback_data: ProductCB, services: Services, user: User
) -> None:
    now_favorite = await services.favorites.toggle(user.id, callback_data.product_id)
    product = await services.catalog.product(callback_data.product_id)
    await screen.edit(
        cb,
        await product_screen(
            services, user, product, category_id=callback_data.category_id, page=callback_data.page
        ),
    )
    await cb.answer(texts.FAVORITE_ADDED if now_favorite else texts.FAVORITE_REMOVED)


@router.callback_query(ProductCB.filter(F.action == "share"))
async def share_product(cb: CallbackQuery, callback_data: ProductCB, bot: Bot) -> None:
    me = await bot.get_me()
    link = f"https://t.me/{me.username}?start=product_{callback_data.product_id}"
    if isinstance(cb.message, Message):
        await cb.message.answer(f"{texts.SHARE_TEXT}\n\n<code>{link}</code>")
    await cb.answer()


# ── Search ───────────────────────────────────────────────────────────────────
@router.callback_query(Nav.filter(F.to == "search"))
async def start_search(cb: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(SearchFlow.query)
    await screen.edit(cb, Screen(text=texts.SEARCH_PROMPT, markup=_back_only()))
    await cb.answer()


@router.message(SearchFlow.query, F.text)
async def run_search(message: Message, services: Services, state: FSMContext) -> None:
    query = (message.text or "").strip()
    if len(query) < 2:
        await message.answer(texts.SEARCH_TOO_SHORT)
        return
    await state.update_data(query=query)
    await state.set_state(None)
    page = await services.catalog.search(query, page=1)
    await _render_search(message, page, edit=False)


@router.callback_query(SearchCB.filter())
async def paginate_search(
    cb: CallbackQuery, callback_data: SearchCB, services: Services, state: FSMContext
) -> None:
    data = await state.get_data()
    query = data.get("query")
    if not query:
        await cb.answer(texts.NOT_FOUND_ALERT, show_alert=True)
        return
    page = await services.catalog.search(query, page=callback_data.page)
    await _render_search(cb, page, edit=True)
    await cb.answer()


async def _render_search(
    event: Message | CallbackQuery, page: Page[Product], *, edit: bool
) -> None:
    if page.is_empty:
        scr = Screen(text=texts.SEARCH_EMPTY, markup=_back_only())
    else:
        scr = Screen(text=f"Найдено: <b>{page.total}</b>", markup=search_results_kb(page))
    if edit and isinstance(event, CallbackQuery):
        await screen.edit(event, scr)
    elif isinstance(event, Message):
        await screen.send(event, scr)
