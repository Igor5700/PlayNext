"""Shared cart-hydration logic used by both CartService and CheckoutService.

Both services need to turn the stored (product_id, quantity) rows into a rich
Cart aggregate, dropping lines whose product vanished or was deactivated. They
differ only in what to do with that staleness (CartService persists the
cleanup; CheckoutService just ignores those lines for the current checkout),
so that decision is left to the caller.
"""

from __future__ import annotations

from playnext.application.ports.unit_of_work import UnitOfWork
from playnext.domain.models import Cart, CartLine


async def hydrate_cart(uow: UnitOfWork, user_id: int) -> tuple[Cart, list[int]]:
    """Build the Cart aggregate for a user in one batched product fetch.

    Returns the hydrated cart and the product ids of any stale lines (product
    missing or deactivated) — the caller decides whether/how to clean those up.
    """
    stored = await uow.cart.lines(user_id)
    if not stored:
        return Cart(user_id=user_id, lines=()), []

    products = {p.id: p for p in await uow.products.get_many([pid for pid, _ in stored])}

    lines: list[CartLine] = []
    stale: list[int] = []
    for product_id, quantity in stored:
        product = products.get(product_id)
        if product is None or not product.is_active:
            stale.append(product_id)
            continue
        lines.append(CartLine(product=product, quantity=quantity))
    return Cart(user_id=user_id, lines=tuple(lines)), stale
