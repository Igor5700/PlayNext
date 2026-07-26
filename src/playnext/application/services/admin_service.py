"""Admin use-cases: catalog management, inventory, orders, users, promos, stats."""

from __future__ import annotations

from playnext.application.dto import PER_PAGE, AdminStats, Page, TopProduct
from playnext.application.ports.repositories import PaymentRow
from playnext.application.ports.unit_of_work import UnitOfWorkFactory
from playnext.core.money import Money
from playnext.domain.errors import (
    CategoryHasSalesHistory,
    CategoryNotFound,
    ProductHasSalesHistory,
    ProductNotFound,
)
from playnext.domain.models import Category, Order, Product, PromoCode, User


class AdminService:
    def __init__(self, uow: UnitOfWorkFactory) -> None:
        self._uow = uow

    # ── Dashboard ────────────────────────────────────────────────────────────
    async def stats(self) -> AdminStats:
        async with self._uow() as uow:
            users_total = await uow.users.count()
            orders_total = await uow.orders.count_all()
            revenue_total = await uow.orders.revenue_total()
            products_active = await uow.products.count_active()
            keys_available = await uow.stock.total_available()
            raw_top = await uow.orders.top_products(limit=5)
            top_ids = [product_id for product_id, _, _ in raw_top]
            products_by_id = {p.id: p for p in await uow.products.get_many(top_ids)}
            top = [
                TopProduct(product=products_by_id[product_id], sold_units=units, revenue=revenue)
                for product_id, units, revenue in raw_top
                if product_id in products_by_id
            ]
        return AdminStats(
            users_total=users_total,
            orders_total=orders_total,
            revenue_total=revenue_total,
            products_active=products_active,
            keys_available=keys_available,
            top_products=tuple(top),
        )

    # ── Categories ───────────────────────────────────────────────────────────
    async def categories(self) -> list[Category]:
        async with self._uow() as uow:
            return await uow.categories.list_all()

    async def category(self, category_id: int) -> Category:
        async with self._uow() as uow:
            category = await uow.categories.get(category_id)
        if category is None:
            raise CategoryNotFound
        return category

    async def create_category(self, *, title: str) -> Category:
        async with self._uow() as uow:
            existing = await uow.categories.list_all()
            sort_order = max((c.sort_order for c in existing), default=0) + 1
            category = await uow.categories.create(title=title, sort_order=sort_order)
            await uow.commit()
        return category

    async def rename_category(self, category_id: int, title: str) -> None:
        await self._update_category(category_id, title=title)

    async def toggle_category(self, category_id: int, active: bool) -> None:
        await self._update_category(category_id, is_active=active)

    async def delete_category(self, category_id: int) -> None:
        async with self._uow() as uow:
            if await uow.stock.has_sold_in_category(category_id):
                raise CategoryHasSalesHistory
            await uow.categories.delete(category_id)
            await uow.commit()

    async def _update_category(self, category_id: int, **fields: object) -> None:
        async with self._uow() as uow:
            await uow.categories.update(category_id, **fields)  # type: ignore[arg-type]
            await uow.commit()

    # ── Products ─────────────────────────────────────────────────────────────
    async def products(self, *, page: int = 1) -> Page[Product]:
        offset = (page - 1) * PER_PAGE
        async with self._uow() as uow:
            items, total = await uow.products.list_all(limit=PER_PAGE, offset=offset)
        return Page(items=tuple(items), total=total, page=page)

    async def product(self, product_id: int) -> Product:
        async with self._uow() as uow:
            product = await uow.products.get(product_id)
        if product is None:
            raise ProductNotFound
        return product

    async def create_product(
        self,
        *,
        category_id: int,
        title: str,
        description: str,
        price: Money,
        image_file_id: str | None,
    ) -> Product:
        async with self._uow() as uow:
            if await uow.categories.get(category_id) is None:
                raise CategoryNotFound
            product = await uow.products.create(
                category_id=category_id,
                title=title,
                description=description,
                price=price,
                image_file_id=image_file_id,
            )
            await uow.commit()
        return product

    async def update_product(self, product_id: int, **fields: object) -> None:
        async with self._uow() as uow:
            await uow.products.update(product_id, **fields)  # type: ignore[arg-type]
            await uow.commit()

    async def toggle_product(self, product_id: int, active: bool) -> None:
        await self.update_product(product_id, is_active=active)

    async def delete_product(self, product_id: int) -> None:
        async with self._uow() as uow:
            if await uow.stock.has_sold(product_id):
                raise ProductHasSalesHistory
            await uow.products.delete(product_id)
            await uow.commit()

    # ── Inventory (keys) ─────────────────────────────────────────────────────
    async def add_keys(self, product_id: int, secrets: list[str]) -> int:
        async with self._uow() as uow:
            if await uow.products.get(product_id) is None:
                raise ProductNotFound
            added = await uow.stock.add_keys(product_id, secrets)
            await uow.commit()
        return added

    async def keys_available(self, product_id: int) -> int:
        async with self._uow() as uow:
            return await uow.stock.count_available(product_id)

    # ── Orders ───────────────────────────────────────────────────────────────
    async def orders(self, *, page: int = 1) -> Page[Order]:
        offset = (page - 1) * PER_PAGE
        async with self._uow() as uow:
            items, total = await uow.orders.list_recent(limit=PER_PAGE, offset=offset)
        return Page(items=tuple(items), total=total, page=page)

    async def order(self, order_id: int) -> Order | None:
        async with self._uow() as uow:
            return await uow.orders.get(order_id)

    # ── Payments ─────────────────────────────────────────────────────────────
    async def payments(self, *, page: int = 1) -> Page[PaymentRow]:
        offset = (page - 1) * PER_PAGE
        async with self._uow() as uow:
            items, total = await uow.payments.list_recent(limit=PER_PAGE, offset=offset)
        return Page(items=tuple(items), total=total, page=page)

    # ── Users ────────────────────────────────────────────────────────────────
    async def users(self, *, page: int = 1) -> Page[User]:
        offset = (page - 1) * PER_PAGE
        async with self._uow() as uow:
            total = await uow.users.count()
            items = await uow.users.list_recent(limit=PER_PAGE, offset=offset)
        return Page(items=tuple(items), total=total, page=page)

    async def set_user_blocked(self, user_id: int, blocked: bool) -> None:
        async with self._uow() as uow:
            await uow.users.set_blocked(user_id, blocked)
            await uow.commit()

    async def broadcast_recipients(self) -> list[int]:
        async with self._uow() as uow:
            return await uow.users.all_ids()

    # ── Promo codes ──────────────────────────────────────────────────────────
    async def promos(self) -> list[PromoCode]:
        async with self._uow() as uow:
            return await uow.promos.list_all()

    async def create_promo(self, promo: PromoCode) -> None:
        async with self._uow() as uow:
            await uow.promos.create(promo)
            await uow.commit()

    async def toggle_promo(self, code: str, active: bool) -> None:
        async with self._uow() as uow:
            await uow.promos.set_active(code, active)
            await uow.commit()
