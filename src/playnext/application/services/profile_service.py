"""Personal account use-cases: profile summary and order history."""

from __future__ import annotations

from playnext.application.dto import PER_PAGE, Page, ProfileSummary
from playnext.application.ports.unit_of_work import UnitOfWorkFactory
from playnext.domain.errors import OrderNotFound
from playnext.domain.models import Order


class ProfileService:
    def __init__(self, uow: UnitOfWorkFactory) -> None:
        self._uow = uow

    async def summary(
        self, user_id: int, *, username: str | None, first_name: str
    ) -> ProfileSummary:
        async with self._uow() as uow:
            user = await uow.users.get_or_create(user_id, username=username, first_name=first_name)
            orders_count = await uow.orders.count_by_user(user_id)
            total_spent = await uow.orders.total_spent_by_user(user_id)
        return ProfileSummary(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            balance=user.balance,
            orders_count=orders_count,
            total_spent=total_spent,
        )

    async def orders(self, user_id: int, *, page: int = 1) -> Page[Order]:
        offset = (page - 1) * PER_PAGE
        async with self._uow() as uow:
            items, total = await uow.orders.list_by_user(user_id, limit=PER_PAGE, offset=offset)
        return Page(items=tuple(items), total=total, page=page)

    async def order(self, user_id: int, order_id: int) -> Order:
        async with self._uow() as uow:
            order = await uow.orders.get(order_id)
        if order is None or order.user_id != user_id:
            raise OrderNotFound
        return order
