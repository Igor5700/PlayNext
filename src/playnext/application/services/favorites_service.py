"""Favorites (wishlist) use-cases."""

from __future__ import annotations

from playnext.application.dto import PER_PAGE, Page
from playnext.application.ports.unit_of_work import UnitOfWorkFactory
from playnext.domain.errors import ProductNotFound
from playnext.domain.models import Product


class FavoritesService:
    def __init__(self, uow: UnitOfWorkFactory) -> None:
        self._uow = uow

    async def list(self, user_id: int, *, page: int = 1) -> Page[Product]:
        offset = (page - 1) * PER_PAGE
        async with self._uow() as uow:
            items, total = await uow.favorites.list_products(user_id, limit=PER_PAGE, offset=offset)
        return Page(items=tuple(items), total=total, page=page)

    async def is_favorite(self, user_id: int, product_id: int) -> bool:
        async with self._uow() as uow:
            return await uow.favorites.is_favorite(user_id, product_id)

    async def toggle(self, user_id: int, product_id: int) -> bool:
        """Add if not favorited, remove if it is. Returns the new state."""
        async with self._uow() as uow:
            if await uow.products.get(product_id) is None:
                raise ProductNotFound
            currently = await uow.favorites.is_favorite(user_id, product_id)
            if currently:
                await uow.favorites.remove(user_id, product_id)
            else:
                await uow.favorites.add(user_id, product_id)
            await uow.commit()
        return not currently
