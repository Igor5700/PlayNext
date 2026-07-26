"""Pure-domain unit tests: money arithmetic and promo logic."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from playnext.core.money import Money, parse_major
from playnext.domain.enums import DiscountType
from playnext.domain.models import Cart, CartLine, Product, PromoCode


def _product(price: int) -> Product:
    return Product(
        id=1, category_id=1, title="X", description="", price=Money.from_major(price), stock=10
    )


def test_money_is_exact_and_currency_safe() -> None:
    assert Money.from_major(19.99).minor == 1999
    assert (Money.from_major(1000) - Money.from_major(1)).minor == 99900
    assert (Money.from_major(150) * 3).minor == 45000


def test_money_formatting_groups_thousands() -> None:
    assert Money.from_major(1_234_567).format().replace(" ", " ") == "1 234 567 ₽"


def test_parse_major_accepts_comma_and_spaces() -> None:
    assert parse_major("1 500,50") == Decimal("1500.50")
    assert parse_major("1500.5") == Decimal("1500.5")
    assert parse_major(" 500 ") == Decimal("500")


def test_parse_major_rejects_garbage() -> None:
    assert parse_major("") is None
    assert parse_major("не число") is None
    assert parse_major("12,34,56") is None
    assert parse_major("inf") is None
    assert parse_major("nan") is None


def test_cart_subtotal() -> None:
    cart = Cart(user_id=1, lines=(CartLine(_product(1500), 2), CartLine(_product(500), 1)))
    assert cart.item_count == 3
    assert cart.subtotal.minor == 350000


def test_promo_percent_discount() -> None:
    promo = PromoCode(code="SALE10", discount_type=DiscountType.PERCENT, value=10)
    assert promo.discount_for(Money.from_major(2000)).minor == 20000


def test_promo_fixed_never_exceeds_subtotal() -> None:
    promo = PromoCode(
        code="BIG", discount_type=DiscountType.FIXED, value=Money.from_major(5000).minor
    )
    assert promo.discount_for(Money.from_major(1000)).minor == 100000  # capped at subtotal


def test_promo_usability_rules() -> None:
    now = datetime.now(UTC)
    expired = PromoCode(
        code="OLD",
        discount_type=DiscountType.PERCENT,
        value=10,
        valid_until=now - timedelta(days=1),
    )
    assert not expired.is_usable(Money.from_major(1000), now=now)

    exhausted = PromoCode(
        code="MAX", discount_type=DiscountType.PERCENT, value=10, max_uses=1, used_count=1
    )
    assert not exhausted.is_usable(Money.from_major(1000), now=now)

    min_gate = PromoCode(
        code="MIN",
        discount_type=DiscountType.PERCENT,
        value=10,
        min_subtotal=Money.from_major(2000),
    )
    assert not min_gate.is_usable(Money.from_major(1000), now=now)
    assert min_gate.is_usable(Money.from_major(2000), now=now)
