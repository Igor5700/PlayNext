"""Data-transfer objects returned by the application layer to presentation.

DTOs are read-only shapes tailored to what a screen needs — the presentation
layer never reaches into domain internals or the database.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from typing import Generic, TypeVar

from playnext.core.money import Money
from playnext.domain.models import Product

T = TypeVar("T")

PER_PAGE = 6


@dataclass(frozen=True, slots=True)
class Page(Generic[T]):
    items: tuple[T, ...]
    total: int
    page: int
    per_page: int = PER_PAGE

    @property
    def pages(self) -> int:
        return max(1, ceil(self.total / self.per_page))

    @property
    def has_prev(self) -> bool:
        return self.page > 1

    @property
    def has_next(self) -> bool:
        return self.page < self.pages

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.per_page

    @property
    def is_empty(self) -> bool:
        return not self.items


@dataclass(frozen=True, slots=True)
class CheckoutPreview:
    subtotal: Money
    discount: Money
    total: Money
    item_count: int
    promo_code: str | None
    balance: Money

    @property
    def has_discount(self) -> bool:
        return self.discount.is_positive

    @property
    def can_afford(self) -> bool:
        return self.balance.minor >= self.total.minor


@dataclass(frozen=True, slots=True)
class ProfileSummary:
    user_id: int
    username: str | None
    first_name: str
    balance: Money
    orders_count: int
    total_spent: Money


@dataclass(frozen=True, slots=True)
class TopProduct:
    product: Product
    sold_units: int
    revenue: Money


@dataclass(frozen=True, slots=True)
class AdminStats:
    users_total: int
    orders_total: int
    revenue_total: Money
    products_active: int
    keys_available: int
    top_products: tuple[TopProduct, ...]
