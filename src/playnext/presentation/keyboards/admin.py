"""Admin panel keyboards."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from playnext.application.dto import Page
from playnext.application.ports.repositories import PaymentRow
from playnext.domain.models import Category, Order, Product, PromoCode, User
from playnext.presentation.callbacks import (
    AdminCatCB,
    AdminCB,
    AdminOrderCB,
    AdminPayCB,
    AdminProdCB,
    AdminPromoCB,
    AdminUserCB,
    Nav,
)
from playnext.presentation.formatting import order_row, payment_row, promo_row, user_row
from playnext.presentation.keyboards.common import add_pagination


def _back(cb: str, text: str = "Назад") -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=cb)


def admin_home_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="Товары", callback_data=AdminProdCB(action="list"))
    kb.button(text="Категории", callback_data=AdminCatCB(action="open"))
    kb.button(text="Заказы", callback_data=AdminOrderCB(action="list"))
    kb.button(text="Платежи", callback_data=AdminPayCB(action="list"))
    kb.button(text="Пользователи", callback_data=AdminUserCB(action="list"))
    kb.button(text="Промокоды", callback_data=AdminPromoCB(action="list"))
    kb.button(text="Рассылка", callback_data=AdminCB(to="broadcast"))
    kb.adjust(2)
    kb.row(InlineKeyboardButton(text="Выйти", callback_data=Nav(to="home").pack()))
    return kb.as_markup()


# ── Categories ───────────────────────────────────────────────────────────────
def admin_categories_kb(categories: list[Category]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for c in categories:
        suffix = "" if c.is_active else " (скрыта)"
        kb.button(
            text=f"{c.title} · {c.product_count}{suffix}",
            callback_data=AdminCatCB(action="open", category_id=c.id),
        )
    kb.adjust(1)
    kb.row(
        InlineKeyboardButton(
            text="Добавить категорию", callback_data=AdminCatCB(action="add").pack()
        )
    )
    kb.row(_back(AdminCB(to="home").pack()))
    return kb.as_markup()


def admin_category_kb(category: Category) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    cid = category.id
    kb.button(text="Название", callback_data=AdminCatCB(action="rename", category_id=cid))
    toggle = "Скрыть" if category.is_active else "Показать"
    kb.button(text=toggle, callback_data=AdminCatCB(action="toggle", category_id=cid))
    kb.button(text="Удалить", callback_data=AdminCatCB(action="del", category_id=cid))
    kb.button(text="Добавить товар", callback_data=AdminProdCB(action="add", product_id=cid))
    kb.adjust(2)
    kb.row(_back(AdminCatCB(action="open").pack()))
    return kb.as_markup()


# ── Products ─────────────────────────────────────────────────────────────────
def admin_products_kb(page: Page[Product]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for p in page.items:
        suffix = "" if p.is_active else " (снят с продажи)"
        kb.button(
            text=f"{p.title} · {p.price.format()} · ключей {p.stock}{suffix}",
            callback_data=AdminProdCB(action="open", product_id=p.id, page=page.page),
        )
    kb.adjust(1)
    add_pagination(
        kb, page=page.page, pages=page.pages, make_cb=lambda pg: AdminProdCB(action="list", page=pg)
    )
    kb.row(_back(AdminCB(to="home").pack()))
    return kb.as_markup()


def admin_product_kb(product: Product, *, page: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    pid = product.id
    kb.button(text="Название", callback_data=AdminProdCB(action="title", product_id=pid, page=page))
    kb.button(text="Цена", callback_data=AdminProdCB(action="price", product_id=pid, page=page))
    kb.button(text="Описание", callback_data=AdminProdCB(action="desc", product_id=pid, page=page))
    kb.button(text="Фото", callback_data=AdminProdCB(action="image", product_id=pid, page=page))
    kb.button(
        text="Добавить ключи",
        callback_data=AdminProdCB(action="keys", product_id=pid, page=page),
    )
    toggle = "Снять с продажи" if product.is_active else "Вернуть в продажу"
    kb.button(text=toggle, callback_data=AdminProdCB(action="toggle", product_id=pid, page=page))
    kb.button(text="Удалить", callback_data=AdminProdCB(action="del", product_id=pid, page=page))
    kb.adjust(2)
    kb.row(_back(AdminProdCB(action="list", page=page).pack()))
    return kb.as_markup()


# ── Orders ───────────────────────────────────────────────────────────────────
def admin_orders_kb(page: Page[Order]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for o in page.items:
        kb.button(
            text=order_row(o),
            callback_data=AdminOrderCB(action="open", order_id=o.id, page=page.page),
        )
    kb.adjust(1)
    add_pagination(
        kb,
        page=page.page,
        pages=page.pages,
        make_cb=lambda pg: AdminOrderCB(action="list", page=pg),
    )
    kb.row(_back(AdminCB(to="home").pack()))
    return kb.as_markup()


def admin_order_kb(page: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(_back(AdminOrderCB(action="list", page=page).pack(), "К заказам"))
    return kb.as_markup()


# ── Payments ─────────────────────────────────────────────────────────────────
def admin_payments_kb(page: Page[PaymentRow]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for p in page.items:
        kb.button(text=payment_row(p), callback_data=AdminPayCB(action="list", page=page.page))
    kb.adjust(1)
    add_pagination(
        kb, page=page.page, pages=page.pages, make_cb=lambda pg: AdminPayCB(action="list", page=pg)
    )
    kb.row(_back(AdminCB(to="home").pack()))
    return kb.as_markup()


# ── Users ────────────────────────────────────────────────────────────────────
def admin_users_kb(page: Page[User]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for u in page.items:
        action = "unblock" if u.is_blocked else "block"
        kb.button(
            text=user_row(u),
            callback_data=AdminUserCB(action=action, user_id=u.id, page=page.page),
        )
    kb.adjust(1)
    add_pagination(
        kb, page=page.page, pages=page.pages, make_cb=lambda pg: AdminUserCB(action="list", page=pg)
    )
    kb.row(_back(AdminCB(to="home").pack()))
    return kb.as_markup()


# ── Promo codes ──────────────────────────────────────────────────────────────
def admin_promos_kb(promos: list[PromoCode]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for promo in promos:
        kb.button(
            text=promo_row(promo), callback_data=AdminPromoCB(action="toggle", code=promo.code)
        )
    kb.adjust(1)
    kb.row(
        InlineKeyboardButton(
            text="Добавить промокод", callback_data=AdminPromoCB(action="add").pack()
        )
    )
    kb.row(_back(AdminCB(to="home").pack()))
    return kb.as_markup()


def admin_back_home_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(_back(AdminCB(to="home").pack(), "В панель администратора"))
    return kb.as_markup()
