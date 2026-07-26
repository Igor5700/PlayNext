"""Integration tests for the checkout use-case against a real (in-memory) DB.

These exercise the exact concurrency-safety guarantees the old code lacked:
atomic wallet debit and no-double-sell of keys.
"""

from __future__ import annotations

import pytest

from playnext.application.services import Services
from playnext.core.money import Money
from playnext.domain.enums import DiscountType, OrderStatus, WalletTxnType
from playnext.domain.errors import InsufficientBalance, OutOfStock
from playnext.domain.models import Product, PromoCode


async def _fund_user(uow_factory, user_id: int, balance_major: int) -> None:
    async with uow_factory() as uow:
        await uow.users.get_or_create(user_id, username="user", first_name="User")
        if balance_major:
            await uow.wallet.apply(
                user_id, type=WalletTxnType.TOPUP, amount=Money.from_major(balance_major)
            )
        await uow.commit()


async def _make_product(services: Services, *, price: int, stock: int) -> Product:
    category = await services.admin.create_category(title="Steam")
    product = await services.admin.create_product(
        category_id=category.id,
        title="GTA V",
        description="demo",
        price=Money.from_major(price),
        image_file_id=None,
    )
    await services.admin.add_keys(product.id, [f"KEY-{i}" for i in range(stock)])
    return product


async def test_checkout_delivers_keys_and_debits_wallet(services, uow_factory) -> None:
    await _fund_user(uow_factory, 1, 5000)
    product = await _make_product(services, price=1000, stock=3)
    await services.cart.add(1, product.id, quantity=2)

    order = await services.checkout.place_order(1)

    assert order.status is OrderStatus.FULFILLED
    assert len(order.all_keys) == 2
    assert len(set(order.all_keys)) == 2  # distinct keys
    assert (await services.wallet.balance(1)).minor == Money.from_major(3000).minor
    assert await services.admin.keys_available(product.id) == 1
    assert (await services.cart.view(1)).is_empty


async def test_insufficient_balance_rolls_back(services, uow_factory) -> None:
    await _fund_user(uow_factory, 2, 100)
    product = await _make_product(services, price=1000, stock=3)
    await services.cart.add(2, product.id, quantity=1)

    with pytest.raises(InsufficientBalance):
        await services.checkout.place_order(2)

    assert await services.admin.keys_available(product.id) == 3  # nothing consumed


async def test_no_double_sell_of_last_key(services, uow_factory) -> None:
    await _fund_user(uow_factory, 10, 5000)
    await _fund_user(uow_factory, 11, 5000)
    product = await _make_product(services, price=1000, stock=1)
    await services.cart.add(10, product.id, quantity=1)
    await services.cart.add(11, product.id, quantity=1)

    await services.checkout.place_order(10)  # grabs the single key
    with pytest.raises(OutOfStock):
        await services.checkout.place_order(11)

    assert await services.admin.keys_available(product.id) == 0


async def test_promo_discount_applied_to_total(services, uow_factory) -> None:
    await _fund_user(uow_factory, 20, 5000)
    product = await _make_product(services, price=1000, stock=5)
    await services.admin.create_promo(
        PromoCode(code="WELCOME10", discount_type=DiscountType.PERCENT, value=10)
    )
    await services.cart.add(20, product.id, quantity=2)

    preview = await services.checkout.preview(20, promo_code="WELCOME10")
    assert preview.discount.minor == Money.from_major(200).minor

    order = await services.checkout.place_order(20, promo_code="WELCOME10")
    assert order.total.minor == Money.from_major(1800).minor
    assert (await services.wallet.balance(20)).minor == Money.from_major(3200).minor
