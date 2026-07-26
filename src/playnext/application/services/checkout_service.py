"""Checkout: turn a cart into a paid, fulfilled order.

`place_order` runs inside a single transaction and relies on row-level locking in
the repositories (`wallet.apply`, `stock.consume`) so two concurrent checkouts can
never double-spend the balance or sell the same key twice — the exact class of bug
the previous JSON-based implementation had.
"""

from __future__ import annotations

from datetime import UTC, datetime

from playnext.application.dto import CheckoutPreview
from playnext.application.ports.unit_of_work import UnitOfWork, UnitOfWorkFactory
from playnext.application.services.cart_support import hydrate_cart
from playnext.core.money import Money
from playnext.domain.enums import OrderStatus, WalletTxnType
from playnext.domain.errors import (
    CartEmpty,
    InsufficientBalance,
    OutOfStock,
    PromoInvalid,
)
from playnext.domain.models import Cart, CartLine, Order, OrderItem, PromoCode


class CheckoutService:
    def __init__(self, uow: UnitOfWorkFactory) -> None:
        self._uow = uow

    async def preview(self, user_id: int, *, promo_code: str | None = None) -> CheckoutPreview:
        async with self._uow() as uow:
            cart = await self._load_cart(uow, user_id)
            subtotal = cart.subtotal
            discount = Money.zero()
            applied: str | None = None
            if promo_code:
                promo = await self._validate_promo(uow, promo_code, subtotal)
                discount = promo.discount_for(subtotal)
                applied = promo.code
            balance = await uow.wallet.get_balance(user_id)
        total = subtotal - discount
        return CheckoutPreview(
            subtotal=subtotal,
            discount=discount,
            total=total,
            item_count=cart.item_count,
            promo_code=applied,
            balance=balance,
        )

    async def place_order(self, user_id: int, *, promo_code: str | None = None) -> Order:
        async with self._uow() as uow:
            cart = await self._load_cart(uow, user_id)
            if cart.is_empty:
                raise CartEmpty

            # 1. Verify availability before charging anything.
            for line in cart.lines:
                available = await uow.stock.count_available(line.product.id)
                if available < line.quantity:
                    raise OutOfStock(
                        user_message=f"«{line.product.title}» — в наличии {available} шт."
                    )

            subtotal = cart.subtotal
            discount = Money.zero()
            promo: PromoCode | None = None
            if promo_code:
                promo = await self._validate_promo(uow, promo_code, subtotal)
                discount = promo.discount_for(subtotal)
            total = subtotal - discount

            balance = await uow.wallet.get_balance(user_id)
            if balance.minor < total.minor:
                raise InsufficientBalance

            # 2. Persist the order shell to obtain an id.
            order = await uow.orders.create(
                Order(
                    id=0,
                    user_id=user_id,
                    status=OrderStatus.PENDING,
                    subtotal=subtotal,
                    discount=discount,
                    total=total,
                    promo_code=promo.code if promo else None,
                    items=tuple(self._to_order_item(line) for line in cart.lines),
                    created_at=datetime.now(UTC),
                )
            )

            # 3. Claim keys (row-locked) and debit the wallet (row-locked).
            for line in cart.lines:
                await uow.stock.consume(line.product.id, line.quantity, order_id=order.id)
            await uow.wallet.apply(
                user_id, type=WalletTxnType.PURCHASE, amount=Money.zero() - total, order_id=order.id
            )
            if promo:
                await uow.promos.increment_uses(promo.code)

            # 4. Finalise.
            await uow.orders.set_status(order.id, OrderStatus.FULFILLED)
            await uow.cart.clear(user_id)
            fulfilled = await uow.orders.get(order.id)
            await uow.commit()

        assert fulfilled is not None
        return fulfilled

    # ── helpers ──────────────────────────────────────────────────────────────
    @staticmethod
    def _to_order_item(line: CartLine) -> OrderItem:
        return OrderItem(
            product_id=line.product.id,
            title=line.product.title,
            unit_price=line.product.price,
            quantity=line.quantity,
        )

    async def _load_cart(self, uow: UnitOfWork, user_id: int) -> Cart:
        cart, _stale = await hydrate_cart(uow, user_id)
        return cart

    async def _validate_promo(self, uow: UnitOfWork, code: str, subtotal: Money) -> PromoCode:
        promo = await uow.promos.get(code.strip().upper())
        if promo is None:
            raise PromoInvalid
        if not promo.is_usable(subtotal, now=datetime.now(UTC)):
            raise PromoInvalid(
                user_message="Промокод недействителен или не подходит для этого заказа."
            )
        return promo
