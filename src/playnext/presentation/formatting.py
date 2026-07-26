"""Render domain objects into HTML screen bodies. Pure functions, easy to test."""

from __future__ import annotations

from datetime import datetime
from html import escape

from playnext.application.dto import AdminStats, CheckoutPreview, ProfileSummary
from playnext.application.ports.repositories import PaymentRow
from playnext.core.money import Money
from playnext.domain.enums import OrderStatus, WalletTxnType
from playnext.domain.models import (
    Cart,
    Category,
    Order,
    Product,
    PromoCode,
    User,
    WalletTransaction,
)
from playnext.presentation.texts import CABINET_TITLE

_ORDER_STATUS = {
    OrderStatus.PENDING: "В обработке",
    OrderStatus.PAID: "Оплачен",
    OrderStatus.FULFILLED: "Выполнен",
    OrderStatus.CANCELLED: "Отменён",
    OrderStatus.REFUNDED: "Возврат",
}

_TXN_LABEL = {
    WalletTxnType.TOPUP: "Пополнение",
    WalletTxnType.PURCHASE: "Покупка",
    WalletTxnType.REFUND: "Возврат",
}


def _e(text: str) -> str:
    return escape(text, quote=False)


def _dt(value: datetime | None) -> str:
    return value.strftime("%d.%m.%Y %H:%M") if value else "—"


def _stock_badge(product: Product) -> str:
    if product.stock <= 0:
        return "Нет в наличии"
    if product.stock < 5:
        return f"Осталось {product.stock} шт."
    return "В наличии"


def product_caption(product: Product, *, in_cart: int = 0, sold_count: int = 0) -> str:
    lines = [f"<b>{_e(product.title)}</b>", ""]
    if product.description:
        lines += [_e(product.description), ""]
    lines.append(f"Цена: <b>{product.price.format()}</b>")
    lines.append(_stock_badge(product))
    if sold_count:
        lines.append(f"Куплено {sold_count} раз")
    if in_cart:
        lines.append(f"В корзине: {in_cart} шт.")
    return "\n".join(lines)


def category_header(category: Category, *, page: int, pages: int) -> str:
    head = f"<b>{_e(category.title)}</b>"
    head += f"\nТоваров: {category.product_count}"
    if pages > 1:
        head += f" · страница {page} из {pages}"
    return head


def cart_text(cart: Cart) -> str:
    lines = ["<b>Корзина</b>", ""]
    for line in cart.lines:
        lines.append(f"{_e(line.product.title)} × {line.quantity} — {line.subtotal.format()}")
    lines += ["", f"Итого: <b>{cart.subtotal.format()}</b>"]
    return "\n".join(lines)


def checkout_text(preview: CheckoutPreview) -> str:
    lines = [
        "<b>Оформление заказа</b>",
        "",
        f"Позиций: {preview.item_count}",
        f"Сумма: {preview.subtotal.format()}",
    ]
    if preview.has_discount:
        lines.append(f"Скидка ({_e(preview.promo_code or '')}): −{preview.discount.format()}")
    lines += [
        f"<b>К оплате: {preview.total.format()}</b>",
        "",
        f"Баланс: {preview.balance.format()}",
    ]
    if not preview.can_afford:
        need = Money(preview.total.minor - preview.balance.minor)
        lines.append(f"Не хватает {need.format()}. Пополните баланс.")
    return "\n".join(lines)


def order_text(order: Order) -> str:
    lines = [
        f"<b>Заказ №{order.id}</b>",
        f"{_ORDER_STATUS.get(order.status, order.status.value)} · {_dt(order.created_at)}",
        "",
    ]
    for item in order.items:
        lines.append(f"{_e(item.title)} × {item.quantity} — {item.subtotal.format()}")
        for key in item.delivered_keys:
            lines.append(f"  <code>{_e(key)}</code>")
    lines.append("")
    if order.discount.is_positive:
        lines.append(f"Скидка: −{order.discount.format()}")
    lines.append(f"<b>Итого: {order.total.format()}</b>")
    return "\n".join(lines)


def order_row(order: Order) -> str:
    status = _ORDER_STATUS.get(order.status, order.status.value)
    return f"№{order.id} · {order.total.format()} · {status}"


def cabinet_text(summary: ProfileSummary) -> str:
    name = f"@{summary.username}" if summary.username else _e(summary.first_name)
    return (
        f"{CABINET_TITLE}\n\n"
        "Здесь собраны ваш профиль, баланс и статистика покупок в PlayNext.\n\n"
        f"{name}\n"
        f"ID <code>{summary.user_id}</code>\n\n"
        f"Баланс: <b>{summary.balance.format()}</b> — доступно для оплаты заказов\n"
        f"Покупок: {summary.orders_count} — всего оформленных заказов\n"
        f"Потрачено: {summary.total_spent.format()} — общая сумма всех покупок\n\n"
        "Пополните баланс в разделе «Баланс», чтобы оформлять заказы мгновенно, "
        "без ввода данных карты при каждой покупке. Все выданные ключи и "
        "историю заказов смотрите в «Мои покупки»."
    )


def wallet_text(balance: Money, *, providers: tuple[str, ...] = ()) -> str:
    has_demo = "demo" in providers
    has_crypto = "crypto_pay" in providers
    if has_demo and has_crypto:
        payment_line = (
            "Пополнить можно двумя способами: демо — мгновенно и бесплатно, для "
            "теста, либо Crypto Pay — реальными деньгами."
        )
    elif has_demo:
        payment_line = (
            "Демо-режим: пополнение мгновенное и бесплатное, реальные деньги не "
            "списываются — можно тестировать покупки без ограничений."
        )
    else:
        payment_line = (
            "Пополнение — через платёжный шлюз Crypto Pay, зачисление обычно "
            "занимает не больше пары минут."
        )
    return (
        "<b>Баланс</b>\n\n"
        f"<b>{balance.format()}</b> доступно для оплаты\n\n"
        "Внутренний счёт PlayNext — пополните его один раз и дальше оформляйте "
        "заказы в один тап, без ввода данных карты каждый раз. Деньги "
        "списываются автоматически при оформлении заказа в корзине, а ключи "
        "выдаются сразу после списания.\n\n"
        f"{payment_line} Историю всех операций по счёту смотрите в «Истории»."
    )


def transaction_row(txn: WalletTransaction) -> str:
    label = txn.note or _TXN_LABEL.get(txn.type, txn.type.value)
    sign = "+" if txn.amount.is_positive else "−"
    status = " · Успешно" if txn.note else ""
    return f"{label}: {sign}{Money(abs(txn.amount.minor)).format()}{status} · {_dt(txn.created_at)}"


def discount_row(promo: PromoCode) -> str:
    kind = (
        f"{promo.value}%" if promo.discount_type.value == "percent" else Money(promo.value).format()
    )
    text = f"<code>{_e(promo.code)}</code> — скидка {kind}"
    if promo.min_subtotal.is_positive:
        text += f", от {promo.min_subtotal.format()}"
    return text


def promo_row(promo: PromoCode) -> str:
    """Plain text — used as an inline button label, which never renders HTML."""
    kind = (
        f"{promo.value}%" if promo.discount_type.value == "percent" else Money(promo.value).format()
    )
    state = "активен" if promo.is_active else "выключен"
    used = f"{promo.used_count}" + (f"/{promo.max_uses}" if promo.max_uses else "")
    return f"{promo.code} — {kind} · {state} · использован {used}"


def user_row(user: User) -> str:
    """Plain text — used as an inline button label, which never renders HTML."""
    name = f"@{user.username}" if user.username else user.first_name
    text = f"{name} · {user.id} · {user.balance.format()}"
    return f"{text} · заблокирован" if user.is_blocked else text


def payment_row(payment: PaymentRow) -> str:
    return f"№{payment.id} · {payment.amount.format()} · {payment.status} · {payment.user_id}"


def admin_stats_text(stats: AdminStats) -> str:
    lines = [
        "<b>Сводка</b>",
        "",
        f"Пользователей: {stats.users_total}",
        f"Заказов: {stats.orders_total}",
        f"Выручка: {stats.revenue_total.format()}",
        f"Активных товаров: {stats.products_active}",
        f"Ключей на складе: {stats.keys_available}",
    ]
    if stats.top_products:
        lines += ["", "<b>Топ товаров</b>"]
        for i, tp in enumerate(stats.top_products, 1):
            lines.append(
                f"{i}. {_e(tp.product.title)} — {tp.sold_units} шт. · {tp.revenue.format()}"
            )
    return "\n".join(lines)
