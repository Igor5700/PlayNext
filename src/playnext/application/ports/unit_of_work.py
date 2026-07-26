"""Unit of Work port.

A UoW wraps a single database transaction and exposes the repositories bound to
it. Services open a UoW per use-case, giving each business operation an explicit,
atomic transaction boundary. `async with uow: ...` rolls back automatically
unless `commit()` was called.
"""

from __future__ import annotations

from types import TracebackType
from typing import Protocol

from playnext.application.ports.repositories import (
    CartRepository,
    CategoryRepository,
    FavoriteRepository,
    OrderRepository,
    PaymentRepository,
    ProductRepository,
    PromoRepository,
    RecentlyViewedRepository,
    StockKeyRepository,
    UserRepository,
    WalletRepository,
)


class UnitOfWork(Protocol):
    users: UserRepository
    categories: CategoryRepository
    products: ProductRepository
    stock: StockKeyRepository
    cart: CartRepository
    promos: PromoRepository
    orders: OrderRepository
    wallet: WalletRepository
    payments: PaymentRepository
    favorites: FavoriteRepository
    recently_viewed: RecentlyViewedRepository

    async def __aenter__(self) -> UnitOfWork: ...
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...
    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...


class UnitOfWorkFactory(Protocol):
    def __call__(self) -> UnitOfWork: ...
