"""Cart repository (stored as thin (user, product, qty) rows)."""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from playnext.infrastructure.db.models import CartItemORM


class CartRepositoryImpl:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def lines(self, user_id: int) -> list[tuple[int, int]]:
        rows = (
            await self._session.execute(
                select(CartItemORM.product_id, CartItemORM.quantity)
                .where(CartItemORM.user_id == user_id)
                .order_by(CartItemORM.product_id)
            )
        ).all()
        return [(row[0], row[1]) for row in rows]

    async def set_quantity(self, user_id: int, product_id: int, quantity: int) -> None:
        row = await self._session.get(CartItemORM, (user_id, product_id))
        if row is None:
            self._session.add(
                CartItemORM(user_id=user_id, product_id=product_id, quantity=quantity)
            )
        else:
            row.quantity = quantity

    async def remove(self, user_id: int, product_id: int) -> None:
        await self._session.execute(
            delete(CartItemORM).where(
                CartItemORM.user_id == user_id, CartItemORM.product_id == product_id
            )
        )

    async def clear(self, user_id: int) -> None:
        await self._session.execute(delete(CartItemORM).where(CartItemORM.user_id == user_id))
