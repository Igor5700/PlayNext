"""SQLAlchemy-backed Unit of Work.

One instance == one session == one transaction. Repositories are created lazily
and bound to that session, so every write inside a `async with uow` block is part
of the same atomic transaction.
"""

from __future__ import annotations

from types import TracebackType

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

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
from playnext.application.ports.unit_of_work import UnitOfWork, UnitOfWorkFactory
from playnext.infrastructure.repositories.cart import CartRepositoryImpl
from playnext.infrastructure.repositories.catalog import (
    CategoryRepositoryImpl,
    ProductRepositoryImpl,
    StockKeyRepositoryImpl,
)
from playnext.infrastructure.repositories.discovery import (
    FavoriteRepositoryImpl,
    RecentlyViewedRepositoryImpl,
)
from playnext.infrastructure.repositories.order import OrderRepositoryImpl
from playnext.infrastructure.repositories.payment import PaymentRepositoryImpl
from playnext.infrastructure.repositories.promo import PromoRepositoryImpl
from playnext.infrastructure.repositories.user import (
    UserRepositoryImpl,
    WalletRepositoryImpl,
)


class SqlAlchemyUnitOfWork:
    # Declared here (not just assigned in __aenter__) so this class structurally
    # satisfies the UnitOfWork protocol for mypy — see module docstring: real
    # values are only bound once the context manager is entered. Typed as the
    # ports (not the concrete *Impl classes): Protocol attribute matching is
    # invariant for mutable fields, and this is also the correct type for
    # callers, who should only ever see the port.
    users: UserRepository
    wallet: WalletRepository
    categories: CategoryRepository
    products: ProductRepository
    stock: StockKeyRepository
    cart: CartRepository
    orders: OrderRepository
    promos: PromoRepository
    payments: PaymentRepository
    favorites: FavoriteRepository
    recently_viewed: RecentlyViewedRepository

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None

    async def __aenter__(self) -> UnitOfWork:
        self._session = self._session_factory()
        session = self._session
        self.users = UserRepositoryImpl(session)
        self.wallet = WalletRepositoryImpl(session)
        self.categories = CategoryRepositoryImpl(session)
        self.products = ProductRepositoryImpl(session)
        self.stock = StockKeyRepositoryImpl(session)
        self.cart = CartRepositoryImpl(session)
        self.orders = OrderRepositoryImpl(session)
        self.promos = PromoRepositoryImpl(session)
        self.payments = PaymentRepositoryImpl(session)
        self.favorites = FavoriteRepositoryImpl(session)
        self.recently_viewed = RecentlyViewedRepositoryImpl(session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        assert self._session is not None
        try:
            if exc is not None:
                await self._session.rollback()
        finally:
            await self._session.close()
            self._session = None

    async def commit(self) -> None:
        assert self._session is not None
        await self._session.commit()

    async def rollback(self) -> None:
        assert self._session is not None
        await self._session.rollback()


def make_uow_factory(session_factory: async_sessionmaker[AsyncSession]) -> UnitOfWorkFactory:
    def factory() -> UnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory)

    return factory
