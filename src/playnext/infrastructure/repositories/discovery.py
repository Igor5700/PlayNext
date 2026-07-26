"""Favorites and recently-viewed repositories.

Both are thin per-user product lists (same shape as the cart), so both hydrate
via ProductRepositoryImpl.get_many — reusing the same session, since every
repository bound to one UnitOfWork shares it — rather than duplicating the
stock-aware product query.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from playnext.domain.models import Product
from playnext.infrastructure.db.models import FavoriteORM, RecentlyViewedORM
from playnext.infrastructure.repositories.catalog import ProductRepositoryImpl


class FavoriteRepositoryImpl:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def is_favorite(self, user_id: int, product_id: int) -> bool:
        row = await self._session.get(FavoriteORM, (user_id, product_id))
        return row is not None

    async def add(self, user_id: int, product_id: int) -> None:
        existing = await self._session.get(FavoriteORM, (user_id, product_id))
        if existing is None:
            self._session.add(FavoriteORM(user_id=user_id, product_id=product_id))
            await self._session.flush()

    async def remove(self, user_id: int, product_id: int) -> None:
        row = await self._session.get(FavoriteORM, (user_id, product_id))
        if row is not None:
            await self._session.delete(row)

    async def list_products(
        self, user_id: int, *, limit: int, offset: int
    ) -> tuple[list[Product], int]:
        total = int(
            await self._session.scalar(
                select(func.count(FavoriteORM.user_id)).where(FavoriteORM.user_id == user_id)
            )
            or 0
        )
        ids = list(
            await self._session.scalars(
                select(FavoriteORM.product_id)
                .where(FavoriteORM.user_id == user_id)
                .order_by(FavoriteORM.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
        )
        return await _hydrate_in_order(self._session, ids), total


class RecentlyViewedRepositoryImpl:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(self, user_id: int, product_id: int) -> None:
        now = datetime.now(UTC)
        row = await self._session.get(RecentlyViewedORM, (user_id, product_id))
        if row is None:
            self._session.add(
                RecentlyViewedORM(user_id=user_id, product_id=product_id, viewed_at=now)
            )
        else:
            row.viewed_at = now
        await self._session.flush()

    async def list_products(self, user_id: int, *, limit: int) -> list[Product]:
        ids = list(
            await self._session.scalars(
                select(RecentlyViewedORM.product_id)
                .where(RecentlyViewedORM.user_id == user_id)
                .order_by(RecentlyViewedORM.viewed_at.desc())
                .limit(limit)
            )
        )
        return await _hydrate_in_order(self._session, ids)


async def _hydrate_in_order(session: AsyncSession, ids: list[int]) -> list[Product]:
    """get_many() doesn't preserve input order — restore it, dropping any id
    that no longer resolves to a product."""
    if not ids:
        return []
    products = {p.id: p for p in await ProductRepositoryImpl(session).get_many(ids)}
    return [products[i] for i in ids if i in products]
