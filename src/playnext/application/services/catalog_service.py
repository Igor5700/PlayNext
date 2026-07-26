"""Catalog browsing use-cases."""

from __future__ import annotations

from playnext.application.dto import PER_PAGE, Page
from playnext.application.ports.unit_of_work import UnitOfWorkFactory
from playnext.domain.errors import CategoryNotFound, ProductNotFound
from playnext.domain.models import Category, Product, PromoCode


class CatalogService:
    def __init__(self, uow: UnitOfWorkFactory) -> None:
        self._uow = uow

    async def categories(self) -> list[Category]:
        async with self._uow() as uow:
            return await uow.categories.list_active()

    async def category(self, category_id: int) -> Category:
        async with self._uow() as uow:
            category = await uow.categories.get(category_id)
        if category is None or not category.is_active:
            raise CategoryNotFound
        return category

    async def products(self, category_id: int, *, page: int = 1) -> Page[Product]:
        offset = (page - 1) * PER_PAGE
        async with self._uow() as uow:
            items, total = await uow.products.list_by_category(
                category_id, limit=PER_PAGE, offset=offset
            )
        return Page(items=tuple(items), total=total, page=page)

    async def product(self, product_id: int) -> Product:
        async with self._uow() as uow:
            product = await uow.products.get(product_id)
        if product is None or not product.is_active:
            raise ProductNotFound
        return product

    async def search(self, query: str, *, page: int = 1) -> Page[Product]:
        offset = (page - 1) * PER_PAGE
        async with self._uow() as uow:
            items, total = await uow.products.search(query.strip(), limit=PER_PAGE, offset=offset)
        return Page(items=tuple(items), total=total, page=page)

    async def newest(self, *, limit: int = PER_PAGE) -> list[Product]:
        async with self._uow() as uow:
            return await uow.products.list_newest(limit=limit)

    async def featured(self, *, limit: int = 5) -> list[Product]:
        async with self._uow() as uow:
            return await uow.products.list_featured(limit=limit)

    async def variant_group(self, group: str) -> list[Product]:
        async with self._uow() as uow:
            return await uow.products.list_by_variant_group(group)

    async def popular(self, *, limit: int = PER_PAGE) -> list[Product]:
        async with self._uow() as uow:
            raw_top = await uow.orders.top_products(limit=limit)
            ids = [product_id for product_id, _, _ in raw_top]
            products = {p.id: p for p in await uow.products.get_many(ids)}
        return [products[i] for i in ids if i in products]

    async def similar(self, product_id: int, *, limit: int = 4) -> list[Product]:
        """Other products in the same category — cheapest possible notion of
        'similar' given there's no genre/tag data yet (see roadmap)."""
        async with self._uow() as uow:
            product = await uow.products.get(product_id)
            if product is None:
                return []
            items, _ = await uow.products.list_by_category(
                product.category_id, limit=limit + 1, offset=0
            )
        return [p for p in items if p.id != product_id][:limit]

    async def sold_count(self, product_id: int) -> int:
        async with self._uow() as uow:
            return await uow.orders.sold_count(product_id)

    async def active_promos(self) -> list[PromoCode]:
        async with self._uow() as uow:
            return await uow.promos.list_active()

    async def record_view(self, user_id: int, product_id: int) -> None:
        async with self._uow() as uow:
            await uow.recently_viewed.record(user_id, product_id)
            await uow.commit()

    async def recently_viewed(self, user_id: int, *, limit: int = 10) -> list[Product]:
        async with self._uow() as uow:
            return await uow.recently_viewed.list_products(user_id, limit=limit)
