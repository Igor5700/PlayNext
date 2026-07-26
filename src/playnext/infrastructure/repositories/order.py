"""Order repository (orders, items, delivered keys, aggregates)."""

from __future__ import annotations

from collections import defaultdict

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from playnext.core.money import Money
from playnext.domain.enums import OrderStatus
from playnext.domain.models import Order
from playnext.infrastructure.db.models import OrderItemORM, OrderORM, StockKeyORM
from playnext.infrastructure.repositories.mappers import to_order, to_order_item

_FULFILLED = OrderStatus.FULFILLED.value


class OrderRepositoryImpl:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, order: Order) -> Order:
        row = OrderORM(
            user_id=order.user_id,
            status=order.status.value,
            subtotal_minor=order.subtotal.minor,
            discount_minor=order.discount.minor,
            total_minor=order.total.minor,
            promo_code=order.promo_code,
            items=[
                OrderItemORM(
                    product_id=item.product_id,
                    title=item.title,
                    unit_price_minor=item.unit_price.minor,
                    quantity=item.quantity,
                )
                for item in order.items
            ],
        )
        self._session.add(row)
        await self._session.flush()
        return to_order(row, tuple(to_order_item(item) for item in row.items))

    async def get(self, order_id: int) -> Order | None:
        row = await self._session.scalar(
            select(OrderORM).where(OrderORM.id == order_id).options(selectinload(OrderORM.items))
        )
        if row is None:
            return None
        keys_by_product = await self._keys_for_order(order_id)
        items = tuple(
            to_order_item(item, keys=tuple(keys_by_product.get(item.product_id, ())))
            for item in row.items
        )
        return to_order(row, items)

    async def _keys_for_order(self, order_id: int) -> dict[int | None, list[str]]:
        rows = (
            await self._session.execute(
                select(StockKeyORM.product_id, StockKeyORM.secret).where(
                    StockKeyORM.order_id == order_id
                )
            )
        ).all()
        mapping: dict[int | None, list[str]] = defaultdict(list)
        for product_id, secret in rows:
            mapping[product_id].append(secret)
        return mapping

    async def _load_list(
        self,
        stmt: Select[tuple[OrderORM]],
        count_stmt: Select[tuple[int]],
        *,
        limit: int,
        offset: int,
    ) -> tuple[list[Order], int]:
        total = int(await self._session.scalar(count_stmt) or 0)
        rows = list(
            await self._session.scalars(
                stmt.options(selectinload(OrderORM.items))
                .order_by(OrderORM.id.desc())
                .limit(limit)
                .offset(offset)
            )
        )
        orders = [to_order(row, tuple(to_order_item(item) for item in row.items)) for row in rows]
        return orders, total

    async def list_by_user(
        self, user_id: int, *, limit: int, offset: int
    ) -> tuple[list[Order], int]:
        return await self._load_list(
            select(OrderORM).where(OrderORM.user_id == user_id),
            select(func.count(OrderORM.id)).where(OrderORM.user_id == user_id),
            limit=limit,
            offset=offset,
        )

    async def list_recent(self, *, limit: int, offset: int) -> tuple[list[Order], int]:
        return await self._load_list(
            select(OrderORM), select(func.count(OrderORM.id)), limit=limit, offset=offset
        )

    async def count_by_user(self, user_id: int) -> int:
        return int(
            await self._session.scalar(
                select(func.count(OrderORM.id)).where(OrderORM.user_id == user_id)
            )
            or 0
        )

    async def total_spent_by_user(self, user_id: int) -> Money:
        total = await self._session.scalar(
            select(func.coalesce(func.sum(OrderORM.total_minor), 0)).where(
                OrderORM.user_id == user_id, OrderORM.status == _FULFILLED
            )
        )
        return Money(int(total or 0))

    async def set_status(self, order_id: int, status: OrderStatus) -> None:
        row = await self._session.get(OrderORM, order_id)
        if row is not None:
            row.status = status.value

    async def count_all(self) -> int:
        return int(await self._session.scalar(select(func.count(OrderORM.id))) or 0)

    async def revenue_total(self) -> Money:
        total = await self._session.scalar(
            select(func.coalesce(func.sum(OrderORM.total_minor), 0)).where(
                OrderORM.status == _FULFILLED
            )
        )
        return Money(int(total or 0))

    async def sold_count(self, product_id: int) -> int:
        total = await self._session.scalar(
            select(func.coalesce(func.sum(OrderItemORM.quantity), 0))
            .join(OrderORM, OrderItemORM.order_id == OrderORM.id)
            .where(OrderItemORM.product_id == product_id, OrderORM.status == _FULFILLED)
        )
        return int(total or 0)

    async def top_products(self, *, limit: int) -> list[tuple[int, int, Money]]:
        units = func.sum(OrderItemORM.quantity)
        revenue = func.sum(OrderItemORM.unit_price_minor * OrderItemORM.quantity)
        rows = (
            await self._session.execute(
                select(OrderItemORM.product_id, units, revenue)
                .join(OrderORM, OrderItemORM.order_id == OrderORM.id)
                .where(OrderORM.status == _FULFILLED, OrderItemORM.product_id.isnot(None))
                .group_by(OrderItemORM.product_id)
                .order_by(units.desc())
                .limit(limit)
            )
        ).all()
        return [(row[0], int(row[1] or 0), Money(int(row[2] or 0))) for row in rows]
