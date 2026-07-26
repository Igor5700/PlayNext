"""Catalog keyboards: home shelf, category grid and product lists."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from playnext.application.dto import Page
from playnext.domain.models import Category, Product
from playnext.presentation.callbacks import (
    CatalogCB,
    CatalogFilterCB,
    FeaturedCB,
    GroupCB,
    Nav,
    Noop,
    ProductCB,
    SearchCB,
)
from playnext.presentation.keyboards.common import add_pagination, back_button


def _stock_mark(product: Product) -> str:
    return "" if product.in_stock else " (нет в наличии)"


def _quick_filters_rows(kb: InlineKeyboardBuilder, *, has_recent: bool) -> None:
    kb.row(InlineKeyboardButton(text="Поиск", callback_data=Nav(to="search").pack()))
    kb.row(
        InlineKeyboardButton(text="Новинки", callback_data=CatalogFilterCB(kind="newest").pack()),
        InlineKeyboardButton(
            text="Популярное", callback_data=CatalogFilterCB(kind="popular").pack()
        ),
    )
    second_row = [
        InlineKeyboardButton(text="Скидки", callback_data=CatalogFilterCB(kind="discounts").pack())
    ]
    if has_recent:
        second_row.append(
            InlineKeyboardButton(
                text="Недавние", callback_data=CatalogFilterCB(kind="recent").pack()
            )
        )
    kb.row(*second_row)


def catalog_home_kb(categories: list[Category], *, has_recent: bool) -> InlineKeyboardMarkup:
    """Category-only catalog home — fallback when there are no featured games."""
    kb = InlineKeyboardBuilder()
    _quick_filters_rows(kb, has_recent=has_recent)
    for category in categories:
        kb.row(
            InlineKeyboardButton(
                text=f"{category.title} · {category.product_count}",
                callback_data=CatalogCB(category_id=category.id).pack(),
            )
        )
    kb.row(back_button("home"))
    return kb.as_markup()


def featured_showcase_kb(
    items: list[Product],
    *,
    index: int,
    current: Product,
    categories: list[Category],
    has_recent: bool,
) -> InlineKeyboardMarkup:
    """Catalog home when there are featured games: a photo showcase card (cycled via
    ◀/▶) on top of the usual quick filters and category list."""
    kb = InlineKeyboardBuilder()
    total = len(items)
    if total > 1:
        kb.row(
            InlineKeyboardButton(
                text="◀", callback_data=FeaturedCB(index=(index - 1) % total).pack()
            ),
            InlineKeyboardButton(text=f"{index + 1}/{total}", callback_data=Noop().pack()),
            InlineKeyboardButton(
                text="▶", callback_data=FeaturedCB(index=(index + 1) % total).pack()
            ),
        )
    if current.variant_group:
        kb.row(
            InlineKeyboardButton(
                text="Выбрать издание",
                callback_data=GroupCB(group=current.variant_group).pack(),
            )
        )
    elif current.in_stock:
        kb.row(
            InlineKeyboardButton(
                text="Купить сейчас",
                callback_data=ProductCB(
                    action="buy_now", product_id=current.id, category_id=current.category_id
                ).pack(),
            ),
            InlineKeyboardButton(
                text="В корзину",
                callback_data=ProductCB(
                    action="add", product_id=current.id, category_id=current.category_id
                ).pack(),
            ),
        )

    _quick_filters_rows(kb, has_recent=has_recent)
    for category in categories:
        kb.row(
            InlineKeyboardButton(
                text=f"{category.title} · {category.product_count}",
                callback_data=CatalogCB(category_id=category.id).pack(),
            )
        )
    kb.row(back_button("home"))
    return kb.as_markup()


def variant_group_kb(members: list[Product]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for product in members:
        if " (" in product.title:
            edition = product.title.split(" (", 1)[1].rstrip(")")
        else:
            edition = product.title
        kb.button(
            text=f"{edition} — {product.price.format()}",
            callback_data=ProductCB(
                action="open", product_id=product.id, category_id=product.category_id, page=1
            ),
        )
    kb.adjust(1)
    kb.row(InlineKeyboardButton(text="К категориям", callback_data=Nav(to="catalog").pack()))
    return kb.as_markup()


def products_kb(page: Page[Product], *, category_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for product in page.items:
        kb.button(
            text=f"{product.title} · {product.price.format()}{_stock_mark(product)}",
            callback_data=ProductCB(
                action="open", product_id=product.id, category_id=category_id, page=page.page
            ),
        )
    kb.adjust(1)
    add_pagination(
        kb,
        page=page.page,
        pages=page.pages,
        make_cb=lambda p: CatalogCB(category_id=category_id, page=p),
    )
    kb.row(InlineKeyboardButton(text="К категориям", callback_data=Nav(to="catalog").pack()))
    return kb.as_markup()


def search_results_kb(page: Page[Product]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for product in page.items:
        kb.button(
            text=f"{product.title} · {product.price.format()}{_stock_mark(product)}",
            callback_data=ProductCB(
                action="open", product_id=product.id, category_id=product.category_id, page=1
            ),
        )
    kb.adjust(1)
    add_pagination(kb, page=page.page, pages=page.pages, make_cb=lambda p: SearchCB(page=p))
    kb.row(back_button("home"))
    return kb.as_markup()


def product_shelf_kb(products: list[Product], *, back_to: str = "catalog") -> InlineKeyboardMarkup:
    """A flat list of products opening their card — used by Newest/Popular/Recent."""
    kb = InlineKeyboardBuilder()
    for product in products:
        kb.button(
            text=f"{product.title} · {product.price.format()}{_stock_mark(product)}",
            callback_data=ProductCB(
                action="open", product_id=product.id, category_id=product.category_id, page=1
            ),
        )
    kb.adjust(1)
    kb.row(InlineKeyboardButton(text="К каталогу", callback_data=Nav(to=back_to).pack()))
    return kb.as_markup()
