"""Cart use-cases.

The stored cart is a thin list of (product_id, quantity). The service hydrates it
into a rich `Cart` aggregate on read, and enforces stock limits on write.
"""

from __future__ import annotations

from playnext.application.ports.unit_of_work import UnitOfWork, UnitOfWorkFactory
from playnext.application.services.cart_support import hydrate_cart
from playnext.domain.errors import ProductNotFound
from playnext.domain.models import Cart


class CartService:
    def __init__(self, uow: UnitOfWorkFactory) -> None:
        self._uow = uow

    async def view(self, user_id: int) -> Cart:
        async with self._uow() as uow:
            return await self._hydrate(uow, user_id)

    async def add(self, user_id: int, product_id: int, *, quantity: int = 1) -> Cart:
        async with self._uow() as uow:
            product = await uow.products.get(product_id)
            if product is None or not product.is_active:
                raise ProductNotFound
            current = dict(await uow.cart.lines(user_id)).get(product_id, 0)
            available = await uow.stock.count_available(product_id)
            new_qty = min(current + quantity, available)
            if new_qty <= 0:
                await uow.cart.remove(user_id, product_id)
            else:
                await uow.cart.set_quantity(user_id, product_id, new_qty)
            await uow.commit()
            return await self._hydrate(uow, user_id)

    async def set_quantity(self, user_id: int, product_id: int, quantity: int) -> Cart:
        async with self._uow() as uow:
            if quantity <= 0:
                await uow.cart.remove(user_id, product_id)
            else:
                available = await uow.stock.count_available(product_id)
                await uow.cart.set_quantity(user_id, product_id, min(quantity, available))
            await uow.commit()
            return await self._hydrate(uow, user_id)

    async def remove(self, user_id: int, product_id: int) -> Cart:
        async with self._uow() as uow:
            await uow.cart.remove(user_id, product_id)
            await uow.commit()
            return await self._hydrate(uow, user_id)

    async def clear(self, user_id: int) -> None:
        async with self._uow() as uow:
            await uow.cart.clear(user_id)
            await uow.commit()

    async def _hydrate(self, uow: UnitOfWork, user_id: int) -> Cart:
        """Build the Cart aggregate, silently dropping products that vanished."""
        cart, stale = await hydrate_cart(uow, user_id)
        if stale:
            for product_id in stale:
                await uow.cart.remove(user_id, product_id)
            await uow.commit()
        return cart
