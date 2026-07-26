"""Pure domain entities.

These carry rich value objects (Money) and business logic. They are storage- and
framework-agnostic: no SQLAlchemy, no aiogram, no Pydantic. Repositories map
persistence rows to and from these types.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from playnext.core.money import Money
from playnext.domain.enums import (
    DiscountType,
    OrderStatus,
    PaymentStatus,
    WalletTxnType,
)


@dataclass(frozen=True, slots=True)
class User:
    id: int
    username: str | None
    first_name: str
    balance: Money
    is_blocked: bool = False
    created_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class Category:
    id: int
    title: str
    sort_order: int = 0
    is_active: bool = True
    product_count: int = 0


@dataclass(frozen=True, slots=True)
class Product:
    id: int
    category_id: int
    title: str
    description: str
    price: Money
    stock: int
    image_file_id: str | None = None
    is_active: bool = True
    is_featured: bool = False
    variant_group: str | None = None
    created_at: datetime | None = None

    @property
    def in_stock(self) -> bool:
        return self.stock > 0


# ── Cart aggregate ──────────────────────────────────────────────────────────
@dataclass(frozen=True, slots=True)
class CartLine:
    product: Product
    quantity: int

    @property
    def subtotal(self) -> Money:
        return self.product.price * self.quantity


@dataclass(frozen=True, slots=True)
class Cart:
    user_id: int
    lines: tuple[CartLine, ...] = ()

    @property
    def is_empty(self) -> bool:
        return not self.lines

    @property
    def item_count(self) -> int:
        return sum(line.quantity for line in self.lines)

    @property
    def subtotal(self) -> Money:
        total = Money.zero()
        for line in self.lines:
            total += line.subtotal
        return total


# ── Promo codes ─────────────────────────────────────────────────────────────
@dataclass(frozen=True, slots=True)
class PromoCode:
    code: str
    discount_type: DiscountType
    value: int  # percent (1..100) or fixed amount in minor units
    is_active: bool = True
    max_uses: int | None = None
    used_count: int = 0
    min_subtotal: Money = field(default_factory=Money.zero)
    valid_until: datetime | None = None

    def is_available(self, *, now: datetime) -> bool:
        """True if the code is in principle usable — active, not expired, not
        exhausted — independent of any particular cart subtotal."""
        if not self.is_active:
            return False
        if self.valid_until is not None and now > self.valid_until:
            return False
        return not (self.max_uses is not None and self.used_count >= self.max_uses)

    def is_usable(self, subtotal: Money, *, now: datetime) -> bool:
        return self.is_available(now=now) and subtotal.minor >= self.min_subtotal.minor

    def discount_for(self, subtotal: Money) -> Money:
        """Return the discount amount, never exceeding the subtotal."""
        if self.discount_type is DiscountType.PERCENT:
            raw = Money(subtotal.minor * self.value // 100, subtotal.currency)
        else:
            raw = Money(self.value, subtotal.currency)
        return raw if raw.minor <= subtotal.minor else subtotal


# ── Orders ──────────────────────────────────────────────────────────────────
@dataclass(frozen=True, slots=True)
class OrderItem:
    product_id: int
    title: str
    unit_price: Money
    quantity: int
    delivered_keys: tuple[str, ...] = ()

    @property
    def subtotal(self) -> Money:
        return self.unit_price * self.quantity


@dataclass(frozen=True, slots=True)
class Order:
    id: int
    user_id: int
    status: OrderStatus
    subtotal: Money
    discount: Money
    total: Money
    items: tuple[OrderItem, ...] = ()
    promo_code: str | None = None
    created_at: datetime | None = None

    @property
    def item_count(self) -> int:
        return sum(item.quantity for item in self.items)

    @property
    def all_keys(self) -> tuple[str, ...]:
        return tuple(key for item in self.items for key in item.delivered_keys)


# ── Wallet ledger ───────────────────────────────────────────────────────────
@dataclass(frozen=True, slots=True)
class WalletTransaction:
    id: int
    user_id: int
    type: WalletTxnType
    amount: Money  # signed: positive in, negative out
    balance_after: Money
    order_id: int | None = None
    note: str | None = None
    created_at: datetime | None = None


# ── External payments (wallet top-ups) ──────────────────────────────────────
@dataclass(frozen=True, slots=True)
class Payment:
    id: int
    user_id: int
    provider: str
    provider_payment_id: str | None
    amount: Money
    status: PaymentStatus
    confirmation_url: str | None = None
    created_at: datetime | None = None
